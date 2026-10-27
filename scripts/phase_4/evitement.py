#!/usr/bin/env python3
"""
Module d'evitement d'obstacles — Phase 4.

Regroupe les capteurs, le filtrage et la logique de decision. Importe par
`obstacle_logic_test.py` (reglage en simulation) et par `mode_receiver.py`
(exploitation). Une seule source de verite pour les constantes calibrees.

Les capteurs ne sont pas initialises a l'import : appeler init_capteurs()
explicitement. Un import ne doit pas reserver de broches GPIO.

Constantes calibrees le 26 octobre 2026 — voir docs/phase4_evitement.md pour
la demarche et les journaux de mesure.

Brochage :
    Capteur   TRIG            ECHO
    Gauche    GPIO23 (Pin 16) GPIO24 (Pin 18)
    Centre    GPIO17 (Pin 11) GPIO27 (Pin 13)
    Droite    GPIO22 (Pin 15) GPIO26 (Pin 37)
"""

from collections import deque
import statistics

# ---------------------------------------------------------------
# Securite
# ---------------------------------------------------------------
D_ARRET   = 20.0  # cm - obstacle de face plus proche -> arret
D_PANIQUE = 15.0  # cm - obstacle plus proche sur N'IMPORTE QUEL capteur
                  #      -> arret, quel que soit l'equilibre des forces.
                  #      Derive de la demi-largeur du chassis. Rattrape le
                  #      blocage symetrique (deux obstacles opposes donnent
                  #      deux repulsions egales, donc une resultante nulle,
                  #      que le champ de potentiel seul interprete comme
                  #      "voie libre") et les obstacles lateraux.

TRAMES_ENTREE = 1  # trame dangereuse -> arret immediat
TRAMES_SORTIE = 8  # trames propres consecutives avant de relacher.
                   # Asymetrie deliberee : un faux arret coute une fraction de
                   # seconde, un arret manque coute le chassis.

# ---------------------------------------------------------------
# Champ de potentiel
# ---------------------------------------------------------------
D_INFLUENCE = 60.0       # cm - au-dela, un obstacle est ignore
D_MIN       = D_PANIQUE  # cm - borne la repulsion.
                         #      Aligne sur D_PANIQUE : en mouvement, aucune
                         #      distance ne descend sous ce seuil sans que
                         #      l'arret soit arme. Une valeur plus basse serait
                         #      du code mort, et conduirait a surestimer la
                         #      correction maximale atteignable.

BASE_SPEED  = 20     # vitesse de croisiere (-100 a 100)
KP_OBS      = 600.0  # gain de correction, calibre empiriquement.
                     #   repulsion max = 1/15 - 1/60 = 0,0500
                     #   correction max = 600 x 0,0500 = 30
                     #   -> consignes -10/50 : pivot differentiel franc
                     #   a 40 cm : 600 x (1/40 - 1/60) = 5 -> 15/25, doux

# ---------------------------------------------------------------
# Capteurs et filtrage
# ---------------------------------------------------------------
PORTEE_MAX  = 4.0   # m
LISSAGE     = 3     # moyennage interne de gpiozero
FENETRE_MED = 5     # fenetre du filtre median
LOOP_PERIOD = 0.1   # s - periode de boucle recommandee (10 Hz)

HORS_PORTEE = PORTEE_MAX * 100.0   # cm

BROCHES = {
    'Gauche': {'trigger': 23, 'echo': 24},
    'Centre': {'trigger': 17, 'echo': 27},
    'Droite': {'trigger': 22, 'echo': 26},
}

_capteurs   = {}
_historique = {}


def init_capteurs():
    """
    Reserve les broches et cree les trois objets DistanceSensor.

    A appeler une seule fois, explicitement. L'import du module ne doit pas
    reserver de GPIO : cela empeche d'importer les constantes depuis un script
    qui n'utilise pas les capteurs.
    """
    global _capteurs, _historique
    if _capteurs:
        return

    from gpiozero import DistanceSensor

    for nom, b in BROCHES.items():
        _capteurs[nom] = DistanceSensor(
            echo=b['echo'], trigger=b['trigger'],
            max_distance=PORTEE_MAX, queue_len=LISSAGE)
        _historique[nom] = deque(maxlen=FENETRE_MED)


def lire(nom):
    """
    Distance filtree en cm, ou None si rien dans la portee.

    Filtre median : elimine completement une valeur aberrante isolee due a la
    diaphonie entre capteurs, la ou une moyenne l'integrerait partiellement.
    Sur la sequence 5,2 -> 54,5 -> 4,2 observee le 26 octobre, la mediane
    renvoie une valeur plausible ; la moyenne aurait renvoye 21 cm, c'est-a-dire
    un obstacle inexistant.
    """
    brut = _capteurs[nom].distance * 100.0
    if brut >= HORS_PORTEE - 1.0:
        brut = HORS_PORTEE

    _historique[nom].append(brut)
    med = statistics.median(_historique[nom])

    return None if med >= HORS_PORTEE - 1.0 else med


def lire_tout():
    """Retourne (gauche, centre, droite) en cm, None si hors portee."""
    return lire('Gauche'), lire('Centre'), lire('Droite')


def amorcer(sleep_fn, periode=LOOP_PERIOD):
    """Remplit la fenetre du filtre median avant la premiere decision."""
    for _ in range(FENETRE_MED):
        lire_tout()
        sleep_fn(periode)


def repulsion(distance):
    """
    Force de repulsion bornee d'un obstacle.

    Nulle au-dela de D_INFLUENCE, croissante quand on approche, plafonnee a
    D_MIN pour rester finie. La forme 1/d - 1/D_INFLUENCE plutot que 1/d assure
    la continuite a la frontiere : la force s'annule exactement en D_INFLUENCE
    au lieu de sauter.
    """
    if distance is None or distance >= D_INFLUENCE:
        return 0.0
    d = max(distance, D_MIN)
    return (1.0 / d) - (1.0 / D_INFLUENCE)


def danger(g, c, d):
    """
    Retourne (bool, motif) : la trame courante est-elle dangereuse.

    Deux criteres independants :
      - obstacle de face sous D_ARRET : le virage n'est plus garanti ;
      - obstacle sous D_PANIQUE sur n'importe quel capteur : le chassis percute
        avant que la correction ait un effet. Ce second critere est absolu, donc
        insensible au blocage symetrique ou la resultante laterale est nulle.
    """
    if c is not None and c < D_ARRET:
        return True, "obstacle de face"

    for nom, dist in (('gauche', g), ('centre', c), ('droite', d)):
        if dist is not None and dist < D_PANIQUE:
            return True, "obstacle a {:.0f} cm ({})".format(dist, nom)

    return False, ""


class Evitement:
    """
    Logique d'evitement avec verrou d'arret asymetrique.

    L'arret est un etat, pas une consequence instantanee de la mesure. Sans
    cette memoire, une seule lecture aberrante renvoyait les moteurs en marche
    avant vers un obstacle a 9 cm (journal du 26 octobre, iteration 1).
    """

    def __init__(self):
        self.arrete = False
        self.compteur_danger = 0
        self.compteur_propre = 0

    def consignes(self, g, c, d):
        """Retourne (gauche, droite, etat) a partir des trois distances."""
        dangereux, motif = danger(g, c, d)

        if dangereux:
            self.compteur_propre = 0
            self.compteur_danger += 1
            if self.compteur_danger >= TRAMES_ENTREE:
                self.arrete = True
        else:
            self.compteur_danger = 0
            if self.arrete:
                self.compteur_propre += 1
                if self.compteur_propre >= TRAMES_SORTIE:
                    self.arrete = False
                    self.compteur_propre = 0

        if self.arrete:
            if dangereux:
                return 0, 0, "ARRET - " + motif
            return 0, 0, "ARRET - degagement {}/{}".format(
                self.compteur_propre, TRAMES_SORTIE)

        rep_g = repulsion(g)
        rep_d = repulsion(d)
        rep_c = repulsion(c)

        # Un obstacle de face ne dit pas de quel cote passer.
        # On reporte sa repulsion sur le cote deja le plus encombre, ce qui
        # pousse le robot vers le cote le plus libre.
        if rep_c > 0:
            if rep_g < rep_d:
                rep_d += rep_c
            else:
                rep_g += rep_c

        force = rep_d - rep_g
        correction = KP_OBS * force

        gauche = max(-100, min(100, int(BASE_SPEED - correction)))
        droite = max(-100, min(100, int(BASE_SPEED + correction)))

        if abs(correction) < 1.0:
            etat = "tout droit"
        elif correction > 0:
            etat = "vire a gauche"
        else:
            etat = "vire a droite"

        return gauche, droite, etat

    def reinitialiser(self):
        """
        Remet le verrou a zero.

        Appele en quittant le mode autonome : au retour, l'etat d'arret ne doit
        pas etre herite d'une situation qui n'existe plus.
        """
        self.arrete = False
        self.compteur_danger = 0
        self.compteur_propre = 0


def fmt(d):
    """Formatage uniforme d'une distance pour l'affichage."""
    return "  ---" if d is None else "{:5.1f}".format(d)
