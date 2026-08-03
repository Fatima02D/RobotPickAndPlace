# Phase 3 — Partie 4 : Fusion inertielle et asservissement de cap

**Statut :** Fusion et asservissement en ligne droite valides. Parcours en carre en cours.
**Date :** Juillet 2026
**Prerequis :** Parties 1 a 3 completes (odometrie encodeurs validee en translation)

---

## Objectif

Corriger la limite mise en evidence en Partie 3 : l'odometrie par encodeurs seuls ne
voit pas le patinage des chenilles. Deux buts distincts :

1. Que l'odometrie sache reellement de combien le robot a tourne (mesure du cap).
2. Que le robot aille physiquement droit (asservissement de cap).

Materiel : centrale inertielle MPU6050 (GY-521), gyroscope trois axes, sur le bus I2C
a l'adresse 0x68.

---

## Rappel du probleme (mesure en Partie 3)

Sur un parcours en ligne droite, le robot deviait reellement de 5 cm au sol, mais
l'odometrie encodeurs seuls n'en voyait que 0,8 cm. Les deux chenilles tournent a la
meme vitesse (les encodeurs le confirment), mais le chassis glisse lateralement. Le
patinage est invisible aux encodeurs par nature : ils mesurent la rotation des roues,
pas le deplacement reel.

---

## Validation du gyroscope

Script : `p3_gyro_test.py`

Le module repond a l'adresse 0x68 (verifie par `i2cdetect -y 1`, aux cotes du Hiwonder
a 0x34).

Resultats de lecture :
- Biais du gyroscope au repos : environ 40 LSB (faible, propre).
- Valeur stable proche de zero robot immobile.
- Reponse proportionnelle a la rotation (plusieurs dizaines de deg/s a la main).
- Signe coherent : rotation gauche positive, rotation droite negative.

Une calibration du biais robot immobile est faite au demarrage de chaque script, sur
200 echantillons. Sans cette calibration, le gyroscope derive de plusieurs degres par
minute meme immobile.

---

## Etape 1 : fusion pour l'odometrie

Script : `p3_odom_fusion.py`

### Principe

Le cap est estime par fusion des deux sources via un filtre complementaire :

```
d_theta = ALPHA * d_theta_gyro + (1 - ALPHA) * d_theta_encodeurs
```

avec ALPHA = 0,98 : le gyroscope domine, car il ne subit pas le patinage. La distance
reste estimee par les encodeurs (le gyroscope ne mesure pas les translations).

### Resultat

Meme parcours en ligne droite qu'en Partie 3 :

| | Encodeurs seuls | Fusion IMU |
|---|---|---|
| Deviation reelle au sol | 5 cm | 7 cm |
| Deviation vue par l'odometrie | 0,8 cm | 4,2 cm |

L'odometrie est passee de "aveugle au patinage" (elle voyait 6 fois trop peu) a "proche
de la realite". Le gyroscope capte bien la rotation reelle du chassis que les encodeurs
rataient.

---

## Etape 2 : asservissement de cap (le robot va droit)

Script : `p3_cap_asservi.py`, puis `p3_cap_distance.py`

### Principe

Le gyroscope ne sert plus seulement a mesurer, mais a corriger. A chaque cycle, l'ecart
entre le cap courant et le cap cible (zero) est calcule, et la commande des moteurs est
ajustee en consequence :

```
erreur = cap_cible - theta
correction = KP * erreur
vitesse_gauche = base - correction
vitesse_droite = base + correction
```

Contrairement a un coefficient fixe, la correction est recalculee en continu a partir de
la deviation reelle mesuree. Elle s'adapte donc au patinage, a la charge de la batterie
et au sol, sans reglage prealable.

### Incident : emballement initial

Au premier essai, le robot est parti en vrille (cap a 144 degres, correction saturee).
Cause : le signe de la correction etait inverse. Au lieu de contre-braquer, le code
amplifiait la deviation (retroaction positive).

Correction : inversion du signe dans la commande moteur
(`set_speed(base + corr, base - corr)`) et reduction du gain par securite.

### Reglage du gain KP

Le gain a ete regle par essais successifs, en observant le comportement au sol :

| KP | Comportement |
|---|---|
| 1,5 | Correction nerveuse, mouvement brusque |
| 0,9 | Un peu vif |
| 0,6 | Doux mais deviation un peu plus grande |
| 0,7 | Retenu : correction douce et deviation reduite |

**KP = 0,7 retenu.**

### Resultat

Progression de la deviation en ligne droite au fil des methodes :

| Methode | Deviation reelle |
|---|---|
| Encodeurs seuls, sans rampe | 11,5 cm |
| Encodeurs + rampe de demarrage | 5 a 7 cm |
| Asservissement gyroscope (KP=0,7) | environ 1 cm sur 82 cm |

Sur 3 metres, avec asservissement : deviation de 3 a 4 cm, cap final toujours sous 2
degres, sur quatre essais. L'asservissement tient le cap sur la distance.

Observation notee : selon les essais, le robot part parfois droit d'emblee, parfois il
devie legerement puis revient sur sa ligne. Cette variabilite reflete le caractere
aleatoire du patinage ; l'asservissement compense a chaque fois, ce qui explique un
resultat final constant malgre un patinage variable. C'est la demonstration concrete de
l'avantage de la boucle fermee sur un coefficient fixe.

---

## Etape 3 : rotation de 90 degres

Script : `p3_tourne90.py`

### Principe

Le robot pivote sur place, l'angle etant integre a partir du gyroscope (vitesse fois
temps). Les moteurs sont coupes avant d'atteindre 90 degres, pour laisser l'inertie
finir la rotation pile a 90.

### Reglage

Premiere approche : vitesse de rotation 12, compensation par une grande tolerance. Rejete
car l'inertie ajoutait environ 22 degres apres la coupure, ce qui est trop et peu fiable
(depend de la charge batterie).

Solution retenue : reduire la vitesse de rotation pour diminuer l'inertie.

| Reglage | Effet |
|---|---|
| TURN_SPEED = 7 | Rotation lente, faible inertie |
| TOLERANCE = 10 | Coupure a 80 deg, l'inertie finit a 90 deg |

Resultat : le gyroscope coupe a environ 80 degres, reproductible a moins de 0,5 degre
pres entre essais, et le robot finit a environ 90 degres au sol. Un virage lent mais
reproductible vaut mieux qu'un virage rapide et imprevisible.

---

## Etape 4 : parcours en carre (en cours)

Script : `p3_carre.py`

Enchainement automatique : avancer 1 m (asservissement de cap), tourner 90 degres, repete
quatre fois. Le robot devrait revenir a son point de depart.

Etat actuel : le robot tourne en avancant au lieu de tracer des cotes droits nets. Le
comportement n'est pas encore correct. A reprendre : verifier que la fonction `avancer`
maintient bien le cap pendant le deplacement, et que l'enchainement avance/rotation ne
melange pas les deux mouvements.

Ce point reste ouvert pour la prochaine session.

---

## Reglages etablis (a conserver)

| Parametre | Valeur | Role |
|---|---|---|
| ALPHA | 0,98 | Poids du gyroscope dans la fusion du cap |
| KP | 0,7 | Gain de l'asservissement de cap en ligne droite |
| TURN_SPEED | 7 | Vitesse de rotation sur place |
| TURN_TOLERANCE | 10 | Marge d'arret avant 90 deg (inertie) |
| METRES_PAR_PULSE | 1,05e-4 | Conversion (avec rampe) |
| ENTRAXE_EFF | 0,219 m | Entraxe effectif |

---

## Bilan de la partie

Les deux objectifs de depart sont atteints en ligne droite :

- Le robot va physiquement droit (asservissement gyroscope, deviation environ 1 %).
- L'odometrie sait ou il est (fusion gyroscope-encodeurs).

La demonstration complete est chiffree : encodeurs seuls (11,5 cm de derive) vers rampe
(5 cm) vers asservissement (1 cm). C'est le resultat principal de la Phase 3.

Reste a finaliser : le parcours en carre, qui validera l'odometrie sur un trajet avec
virages, et fournira la mesure d'erreur de bouclage (ecart entre l'arrivee et le depart).
