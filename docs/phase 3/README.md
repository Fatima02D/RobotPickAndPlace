# Phase 3 — Odometrie

**Statut :** En cours
**Periode :** Juillet 2026
**Prerequis :** Phase 2 validee (teleoperation fonctionnelle)

---

## Objectif de la phase

Doter le robot d'une estimation de sa propre position. A l'issue de cette phase, le
robot doit pouvoir repondre, a tout instant, a la question : ou suis-je par rapport a
mon point de depart ?

Cette estimation prend la forme d'une pose dans le plan :

- `x` — deplacement longitudinal, en metres
- `y` — deplacement lateral, en metres
- `theta` — cap, en radians

Le repere est celui du point de depart, fixe au sol au moment de l'initialisation.

### Pourquoi cette phase est necessaire

La Phase 5 exige une navigation autonome d'un point A vers un point B. Un robot
incapable d'estimer sa position ne peut ni savoir qu'il progresse vers sa cible, ni
savoir qu'il est arrive. L'odometrie est la condition prealable a toute forme de
navigation.

### Distinction avec l'asservissement

Une confusion frequente merite d'etre levee. Faire rouler le robot droit et savoir ou
il se trouve sont deux problemes distincts.

**Rouler droit** releve de l'asservissement : on compare les vitesses des deux chaines
de propulsion et on corrige celle qui devie. C'est un probleme de commande.

**Savoir ou l'on est** releve de l'odometrie : on integre les rotations de roues pour
estimer une pose. C'est un probleme d'estimation.

Un robot peut rouler parfaitement droit et posseder une odometrie fausse. L'inverse est
egalement possible. Les deux problemes sont traites separement, dans cet ordre : le
desequilibre moteur est caracterise en premier, parce qu'un biais systematique sur la
propulsion corrompt l'estimation de pose de maniere cumulative.

---

## Structure de la phase

La phase est decoupee en quatre parties, dans un ordre dicte par les dependances.

| Partie | Objet | Statut |
|---|---|---|
| 1 | Caracterisation du desequilibre moteur | Complete |
| 2 | Relation impulsions vers distance metrique | A faire |
| 3 | Integration de pose par odometrie differentielle | A faire |
| 4 | Quantification de la derive et fusion inertielle | A faire |

---

## Partie 1 — Caracterisation du desequilibre moteur

**Statut : complete.** Document detaille : `Phase3_Calibration_Moteurs.md`

### Probleme traite

Sous consigne identique appliquee aux deux moteurs, le robot devie systematiquement de
sa trajectoire. La deviation est constante en direction, ce qui exclut une cause
aleatoire.

### Methode

Le module Hiwonder expose les compteurs d'encodeurs cumules au registre 60
(`MOTOR_ENCODER_TOTAL_ADDR`), sous forme de quatre entiers 32 bits signes en
little-endian.

Protocole : lecture des compteurs, application d'une consigne symetrique pendant une
duree fixe, arret, seconde lecture. Le ratio des increments quantifie le desequilibre.

Dix-huit essais, repartis sur six points de fonctionnement : consignes 30, 50 et 80, en
marche avant et en marche arriere, trois essais par point. Robot au sol, chenilles en
contact avec la surface reelle.

### Resultats

| Consigne | Ratio D/G | Ecart-type |
|---|---|---|
| +30 | 1,0408 | 0,0028 |
| -30 | 1,0345 | 0,0048 |
| +50 | 1,0378 | 0,0086 |
| -50 | 1,0348 | 0,0099 |
| +80 | 1,0423 | 0,0050 |
| -80 | 1,0342 | 0,0087 |

Ecart entre points de fonctionnement : 0,8 %
Ecart-type maximal : 1,0 %

### Interpretation

Le moteur droit tourne environ 4 % plus vite que le gauche sous consigne identique. Le
signe du biais est invariant sur les dix-huit essais, ce qui etablit son caractere
systematique.

L'ecart entre points de fonctionnement (0,8 %) est inferieur a la dispersion observee
entre essais identiques (jusqu'a 1,0 %). Le desequilibre est donc constant sur toute la
plage : il ne depend ni de la consigne, ni du sens de rotation.

Ce resultat n'allait pas de soi. Un moteur a courant continu n'a aucune obligation de
presenter un desequilibre lineaire, et une calibration effectuee a une seule vitesse
aurait pu se reveler fausse ailleurs. La mesure a six points etait necessaire, non
redondante.

### Correction retenue

Les deux conditions de viabilite d'une correction en boucle ouverte — reproductibilite
et constance — sont satisfaites. Un coefficient multiplicatif unique est donc justifie.

**K_RIGHT = 0,9639**, applique a la consigne du moteur droit avant l'ecriture I2C.

Derive residuelle attendue : environ 1 %, soit de l'ordre de 10 cm sur 10 m parcourus.
Cette derive provient du patinage des chenilles et de la variabilite de la surface.
Aucun coefficient fixe ne peut la supprimer.

### Limites assumees

La correction en boucle ouverte presente trois limites structurelles, enoncees plutot
que masquees.

Elle est calibree a un etat de charge donne : le couple d'un moteur a courant continu
depend de la tension d'alimentation, et le desequilibre peut evoluer a mesure que la
batterie se decharge.

Elle ne s'adapte pas : usure mecanique, changement de surface, charge embarquee
supplementaire ne sont pas pris en compte.

Elle ne supprime pas la derive residuelle de 1 %.

La reponse structurelle a ces limites est l'asservissement en boucle fermee sur les
encodeurs. Cette evolution est retenue pour une iteration ulterieure : la correction
actuelle est suffisante pour la teleoperation et ne bloque pas la suite de la phase.

---

## Partie 2 — Relation impulsions vers distance metrique

**Statut : a faire.**

### Probleme a traiter

L'integration de pose exige de convertir un nombre d'impulsions d'encodeur en une
distance parcourue au sol, exprimee en metres. Cette conversion repose sur deux
grandeurs :

- nombre d'impulsions par tour de roue
- circonference de la roue

Valeurs actuellement retenues, heritees d'une calibration anterieure :

| Grandeur | Valeur |
|---|---|
| Impulsions par tour, moteur gauche | 6648 |
| Impulsions par tour, moteur droit | 6658 |
| Circonference de roue | 15,71 cm |
| Entraxe | 16 cm |

### Anomalie a resoudre au prealable

Les mesures de la Partie 1 ont revele un comportement qui n'est pas explique.

Sur une duree fixe de trois secondes, les compteurs accumulent environ 6800 impulsions
a la consigne 30, et environ 7300 impulsions a la consigne 80. Une augmentation de
consigne de 167 % ne produit qu'une augmentation de 7 % de la distance parcourue.

Deux hypotheses, non departagees a ce stade :

1. Les moteurs saturent bien en dessous de la consigne maximale, et la plage utile de
   la consigne est en realite tres etroite.
2. La consigne du module Hiwonder n'est pas lineaire en vitesse, et sa relation avec la
   vitesse reelle reste a etablir.

Cette anomalie n'affecte pas la calibration de la Partie 1, qui repose sur un ratio et
non sur une valeur absolue. Elle est en revanche bloquante pour la Partie 3 : sans
relation etablie entre impulsions et distance reelle, l'estimation de pose sera fausse,
quelle que soit la qualite de l'integration.

### Mesure prevue

Faire parcourir au robot une distance connue, mesuree au metre ruban sur le sol, et
relever le nombre d'impulsions accumulees. Repeter a plusieurs consignes et sur
plusieurs distances.

Deux resultats attendus : le facteur de conversion impulsions vers metres, et la reponse
a l'anomalie ci-dessus.

Une verification s'impose egalement sur l'entraxe. La valeur de 16 cm est une mesure
geometrique du chassis. Sur un vehicule a chenilles, l'entraxe effectif — celui qui
gouverne la relation entre difference de vitesse des chenilles et vitesse de rotation du
chassis — differe de l'entraxe geometrique, parce que les chenilles glissent
lateralement en virage. Cet entraxe effectif doit etre determine experimentalement, par
rotation sur place d'un angle connu.

---

## Partie 3 — Integration de pose par odometrie differentielle

**Statut : a faire.**

### Principe

A chaque cycle, les increments d'impulsions des deux chaines sont lus et convertis en
distances parcourues par chaque chenille, `d_gauche` et `d_droite`.

La distance parcourue par le centre du robot et la variation de cap s'en deduisent :

```
d_centre = (d_gauche + d_droite) / 2
d_theta  = (d_droite - d_gauche) / entraxe_effectif
```

La pose est ensuite integree :

```
theta += d_theta
x     += d_centre * cos(theta)
y     += d_centre * sin(theta)
```

### Points d'attention

**Frequence d'integration.** Une frequence trop faible degrade l'approximation : entre
deux lectures, la trajectoire est supposee rectiligne, ce qui est d'autant plus faux que
l'intervalle est long. Frequence visee : 20 Hz.

**Robustesse aux lectures corrompues.** L'integration est cumulative : une lecture
aberrante n'est jamais rattrapee, son erreur persiste indefiniment dans la pose. Compte
tenu de l'historique de defaillances du bus I2C sur ce montage, un filtre de plausibilite
sur les increments est indispensable. Un increment physiquement impossible — superieur a
ce que les moteurs peuvent produire en un cycle — doit etre rejete.

**Debordement des compteurs.** Les compteurs sont des entiers 32 bits signes. Le
debordement est lointain, mais l'integration doit porter sur les increments, jamais sur
les valeurs absolues, afin d'y etre insensible.

### Validation prevue

Trois essais, du plus simple au plus revelateur.

**Ligne droite.** Parcours de 2 m mesures au sol. L'odometrie doit annoncer 2 m, avec
`y` et `theta` proches de zero. Ecart tolere a determiner.

**Rotation sur place.** Rotation de 360 degres. L'odometrie doit annoncer un tour
complet, et la position finale doit coincider avec la position initiale.

**Parcours en carre.** Quatre segments de 1 m separes par quatre rotations de 90 degres.
Le robot doit revenir a son point de depart. L'ecart entre la position finale reelle et
la position finale estimee constitue la mesure de l'erreur d'odometrie.

Le parcours en carre est le plus informatif : il accumule les erreurs de translation et
de rotation, et il est representatif d'un deplacement reel.

---

## Partie 4 — Quantification de la derive et fusion inertielle

**Statut : a faire.**

### Probleme attendu

Les encodeurs comptent les rotations des moteurs, non le deplacement reel du chassis.
Sur un vehicule a chenilles, ces deux grandeurs divergent : les chenilles patinent, et
elles patinent particulierement en virage, ou elles glissent lateralement par
construction.

Consequence : l'encodeur enregistre une rotation que le robot n'a pas effectuee. L'erreur
de cap s'accumule et ne se corrige jamais. Apres plusieurs virages, l'estimation de cap
peut s'ecarter significativement de la realite, et toute l'estimation de position en
decoule.

### Materiel disponible

Deux modules MPU6050 (GY-521), centrale inertielle six axes — accelerometre trois axes
et gyroscope trois axes. Interface I2C, adresse par defaut 0x68, sans conflit avec le
module Hiwonder (0x34). Les connecteurs restent a souder.

Le gyroscope mesure la vitesse de rotation reelle du chassis, independamment du
patinage. C'est precisement la grandeur que les encodeurs estiment mal.

### Demarche retenue

La derive angulaire est **d'abord quantifiee**, puis la fusion est implementee.

Cet ordre est deliberе. Sans mesure prealable de la derive, il est impossible de
demontrer que la fusion apporte quelque chose. Un rapport qui affirme avoir ajoute une
centrale inertielle est faible. Un rapport qui etablit une derive de N degres sur dix
virages, puis demontre sa reduction a M degres apres fusion, constitue une contribution
mesurable.

Protocole de quantification : execution repetee du parcours en carre, relevé de l'ecart
entre le cap reel — mesure au sol — et le cap estime par les encodeurs seuls. La derive
est exprimee en degres par virage.

### Fusion

L'architecture retenue repartit les roles selon la fiabilite de chaque capteur :

- **distance parcourue** — encodeurs. Le gyroscope ne mesure pas les translations.
- **cap** — gyroscope, ou fusion ponderee des deux sources.

Un filtre complementaire constitue le point de depart. Il est simple, peu couteux en
calcul, et suffisant lorsque les roles des capteurs sont clairement separes. Un filtre
de Kalman n'est envisage que si le filtre complementaire se revele insuffisant, et sa
necessite devra alors etre demontree, non postulee.

### Validation prevue

Comparaison directe : meme parcours en carre, execute avec odometrie encodeurs seuls,
puis avec fusion inertielle. La metrique est l'ecart de position finale au point de
depart, mesure au sol.

---

## Etat du materiel

| Element | Etat |
|---|---|
| Encodeurs Hiwonder | Operationnels, registre 60 valide en lecture |
| Correction du desequilibre moteur | Implementee, K_RIGHT = 0,9639 |
| MPU6050 (x2) | En stock, connecteurs a souder |
| Bus I2C | Operationnel apres refection de la masse |

---

## Dependance a resoudre

La liaison de masse entre le Raspberry Pi et le module Hiwonder a presente un contact
defectueux, provoquant des echecs intermittents du bus I2C. Voir
`Phase2_Troubleshooting_PartD.md`, section D.4.

Cette liaison doit etre securisee avant l'implementation de la Partie 3. L'odometrie lit
les encodeurs en continu a 20 Hz, et son integration est cumulative : une lecture
corrompue introduit une erreur permanente dans la pose. Construire une estimation de
position sur un bus intermittent revient a accumuler du bruit.

---

## Criteres de completion de la phase

- La conversion impulsions vers metres est etablie et validee au sol
- L'entraxe effectif est determine experimentalement
- La pose (x, y, theta) est estimee et publiee a 20 Hz
- La derive du parcours en carre est quantifiee, encodeurs seuls
- L'apport de la fusion inertielle est mesure et documente

La phase est complete lorsque le robot peut annoncer sa position avec une erreur
caracterisee — non pas nulle, mais connue et bornee.
