#!/usr/bin/env python3
"""
Phase 4 - Reglage de la logique d'evitement, SANS moteurs.

Lit les trois capteurs et affiche les consignes qui seraient envoyees au
controleur moteur, sans rien actionner. Permet de regler les constantes en
securite.

Toute la logique vit dans evitement.py : ce script n'est qu'un afficheur.
Les constantes se modifient donc dans evitement.py, et le reglage trouve ici
est automatiquement celui utilise par mode_receiver.py.

Materiel requis : Raspberry Pi + 3x HC-SR04 uniquement.
Aucun besoin de LiPo, de convertisseur ou de controleur moteur.

Usage :
    python3 obstacle_logic_test.py
"""

import time
import evitement as ev

print("Initialisation des capteurs...")
ev.init_capteurs()
print("Initialisation OK")

print("Remplissage de la fenetre du filtre median...")
ev.amorcer(time.sleep)

print("\nLogique d'evitement - MODE SIMULATION (aucun moteur actionne)")
print("KP_OBS = {:.0f}   D_PANIQUE = {:.0f} cm   hysterese {}/{}".format(
    ev.KP_OBS, ev.D_PANIQUE, ev.TRAMES_ENTREE, ev.TRAMES_SORTIE))
print("Ctrl+C pour arreter\n")
print(" Gauche Centre Droite |  Mot.G  Mot.D  |  Decision")
print("-" * 72)

logique = ev.Evitement()

try:
    while True:
        g, c, d = ev.lire_tout()
        mg, md, etat = logique.consignes(g, c, d)

        print(" {} {} {} |  {:5d}  {:5d}  |  {}".format(
            ev.fmt(g), ev.fmt(c), ev.fmt(d), mg, md, etat))

        time.sleep(ev.LOOP_PERIOD)

except KeyboardInterrupt:
    print("\n\nArret.")
