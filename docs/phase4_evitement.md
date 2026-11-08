# Phase 4 — Évitement d'obstacles réactif

**Statut :** Complète
**Période :** Septembre — Novembre 2026
**Prérequis :** Phase 3 validée (odométrie et asservissement de cap)

---

## Objectif de la phase

Doter le robot de la capacité de modifier sa trajectoire pour éviter un obstacle détecté,
sans intervention humaine. À l'issue de cette phase, le robot doit transformer en continu
trois mesures de distance en deux consignes de vitesse, une par chaîne de propulsion.

La formulation est volontairement étroite. Il ne s'agit pas de planifier un chemin ni de
cartographier l'environnement — ces questions relèvent des Phases 5 et 6. Il s'agit
uniquement de réagir à ce que les capteurs voient maintenant.

### Pourquoi cette phase est nécessaire

La Phase 5 exige une navigation autonome d'un point A vers un point B. Un robot capable de
rejoindre une cible mais incapable de contourner un obstacle sur sa route n'est pas
utilisable hors d'un environnement préparé. L'évitement réactif est la couche de sécurité
sur laquelle la planification s'appuiera.

### Distinction avec la navigation

Une confusion mérite d'être levée dès maintenant, car elle détermine le choix de méthode.

**Naviguer** consiste à atteindre un objectif : le robot connaît sa cible, estime sa pose,
et calcule une trajectoire. C'est un problème global, qui demande une représentation de
l'espace.

**Éviter** consiste à ne pas heurter : le robot ne connaît que ce que ses capteurs lui
rapportent à l'instant présent. C'est un problème local, qui ne demande aucune
représentation.

Les deux couches coexisteront en Phase 5, l'évitement ayant priorité sur la navigation.
Elles sont développées séparément, dans cet ordre, parce qu'un planificateur de trajectoire
construit au-dessus d'une couche d'évitement non validée est impossible à déboguer : toute
anomalie de comportement peut provenir des deux niveaux.

---

## Structure de la phase

| Partie | Objet | Statut |
|---|---|---|
| 1 | Validation matérielle des trois capteurs à ultrasons | Complète |
| 2 | Logique d'évitement par champ de potentiel | Complète |
| 3 | Manœuvre de dégagement et intégration aux moteurs | Complète |
| 4 | Sélecteur de mode à la manette | Complète |

Les Parties 1 et 2 ont été conduites sans actionneurs : le contrôleur moteur Hiwonder
avait été détruit par une défaillance d'alimentation (voir `troubleshooting.md`, F1), et
il a fallu dix jours pour le remplacer. Cette contrainte s'est révélée être un avantage
méthodologique plutôt qu'un obstacle, pour les raisons exposées en fin de document.

---

# Partie 1 — Validation matérielle des capteurs

## Montage

Trois capteurs HC-SR04 sont disposés à l'avant du châssis : un orienté vers l'avant, deux
orientés latéralement.

| Capteur | TRIG | ECHO |
|---|---|---|
| Gauche | GPIO23 (broche 16) | GPIO24 (broche 18) |
| Centre | GPIO17 (broche 11) | GPIO27 (broche 13) |
| Droite | GPIO22 (broche 15) | GPIO26 (broche 37) |

L'alimentation des trois capteurs est prise sur un rail dédié, jamais sur une mini-plaque
d'essai. Les mini-plaques ont été identifiées comme la source des courts-circuits ayant
provoqué l'échauffement des fils lors des premiers essais.

Les sorties ECHO délivrent un signal à 5 V, incompatible avec les entrées du Raspberry Pi
limitées à 3,3 V. Un diviseur de tension est intercalé sur chaque ligne ECHO. Le détail du
calcul figure dans `hardware.md`.

## Choix de la bibliothèque

Le premier script utilisait `RPi.GPIO` avec un chronométrage manuel des impulsions. Sous
Raspberry Pi OS Bookworm, cette bibliothèque passe par une couche de compatibilité `lgpio`
qui ne libère pas correctement les broches lorsqu'un script se termine anormalement. La
conséquence est une erreur `GPIO not allocated` persistante, qui survit à l'arrêt du
processus.

La réécriture utilise `gpiozero.DistanceSensor`, bibliothèque native de Bookworm. Elle gère
le chronométrage en interne et libère les broches de manière fiable.

## Incident : broches réservées par un overlay résiduel

Après la réécriture, l'erreur persistait sous une autre forme :

```
lgpio.error: 'GPIO busy'
```

Un redémarrage complet n'y changeait rien, ce qui excluait un processus résiduel. La cause
était une ligne ajoutée dans `/boot/firmware/config.txt` plusieurs semaines auparavant,
lors du dépannage du bus I2C :

```
dtoverlay=i2c-gpio,bus=3,i2c_gpio_sda=23,i2c_gpio_scl=24
```

Cet overlay créait un bus I2C logiciel sur GPIO23 et GPIO24 — exactement les deux broches
du capteur gauche. Le noyau réservait ces lignes au démarrage, avant que `gpiozero` ne
puisse les demander.

La ligne a été commentée plutôt que supprimée, afin de conserver la trace de l'essai.

**Leçon retenue.** Une modification de `config.txt` survit à tous les redémarrages et
n'apparaît dans aucun message d'erreur : l'erreur indique seulement qu'une broche est
occupée, jamais par quoi. Toute broche affectée à un overlay doit être notée au moment de
l'ajout et l'overlay retiré dès la fin de l'essai.

## Résultat

Les trois capteurs répondent indépendamment. Un obstacle placé devant chacun est détecté
sans influence sur les deux autres. La perception de la Phase 4 est fonctionnelle sans le
contrôleur moteur.

---

# Partie 2 — Logique d'évitement par champ de potentiel

## Choix de méthode

Deux approches étaient envisageables.

Une **machine à états** avec des seuils discrets : si l'obstacle est à moins de tant,
alors tourner. Simple à écrire, mais produit des comportements saccadés aux frontières des
états, et oscille lorsqu'une mesure fluctue autour d'un seuil.

Un **champ de potentiel** : chaque obstacle exerce une force de répulsion dont l'intensité
croît quand la distance décroît. On somme les forces et on applique une correction
proportionnelle à la résultante.

La seconde a été retenue pour sa continuité. Il n'existe aucun seuil où le comportement
bascule : la correction varie progressivement avec la distance, ce qui élimine par
construction l'oscillation entre deux modes.

## Formulation

La force de répulsion d'un obstacle à distance `d` s'écrit :

```
F(d) = 1/d − 1/D_INFLUENCE        pour D_MIN ≤ d < D_INFLUENCE
F(d) = 0                          pour d ≥ D_INFLUENCE
```

La borne inférieure `D_MIN` est nécessaire : sans elle, la force diverge quand la distance
tend vers zéro. La forme `1/d − 1/D_INFLUENCE` plutôt que `1/d` assure la continuité en
`D_INFLUENCE` : la force s'annule exactement à la frontière, au lieu de sauter.

La force latérale nette est la différence des répulsions droite et gauche :

```
force = F(droite) − F(gauche)
correction = KP_OBS × force

consigne_gauche = BASE_SPEED − correction
consigne_droite = BASE_SPEED + correction
```

Un obstacle détecté par le capteur central pose un problème particulier : il ne contient
aucune information sur le côté par lequel passer. Sa répulsion est donc reportée sur le
côté déjà le plus encombré, ce qui pousse le robot vers le côté le plus libre.

## Mode simulation

Le script calcule et affiche les consignes sans les transmettre au contrôleur moteur. Ce
choix était initialement imposé par la panne du Hiwonder, mais il s'est avéré être la bonne
méthode indépendamment : les trois défauts décrits ci-dessous auraient tous conduit le
robot dans un obstacle, et aucun n'aurait été identifiable en observant un robot en
mouvement.

Le format de sortie est une ligne par trame, à 10 Hz :

```
 Gauche Centre Droite |  Mot.G  Mot.D  |  Decision
  36.6   37.9   28.0  |     16     23  |  vire a gauche
```

---

## Itération 1 — Le champ de potentiel nu

Paramètres initiaux : `D_INFLUENCE = 60 cm`, `D_MIN = 10 cm`, `BASE_SPEED = 20`,
`KP_OBS = 200`, arrêt si le capteur central lit moins de 20 cm.

Trois défauts ont été relevés sur les journaux.

### Défaut 1 — Gain structurellement insuffisant

Face à un obstacle à 3,6 cm, soit la proximité maximale physiquement mesurable :

```
   3.6  33.6  32.4  |     36      3  |  vire a droite
```

Les deux consignes restent positives. Le robot dévie mais continue d'avancer vers
l'obstacle.

La cause est arithmétique et non un mauvais réglage. La répulsion est plafonnée par
`D_MIN` :

```
F_max = 1/10 − 1/60 = 0,0833
```

La correction maximale atteignable valait donc `200 × 0,0833 = 16,7` sur une base de 20.
Aucune valeur de distance ne pouvait produire l'inversion d'une chenille. La limite était
dans la structure du calcul, pas dans les mesures.

### Défaut 2 — Diaphonie entre capteurs

```
   5.9   6.5  54.5
   6.5   6.5 ---
   6.8   6.5 ---
   6.8   6.8   4.2
```

Le capteur droit passe de 54,5 cm à hors-portée puis à 4,2 cm en trois dixièmes de seconde.
Physiquement impossible.

Ailleurs dans le même journal, dix trames consécutives identiques au dixième de centimètre
près : `gpiozero` renvoie sa dernière valeur en cache lorsqu'aucun écho ne revient.

L'origine est la diaphonie. Les trois capteurs émettent presque simultanément dans leurs
fils d'exécution respectifs, et à courte distance l'impulsion d'un capteur atteint le
récepteur d'un autre.

### Défaut 3 — L'arrêt d'urgence ne tient pas

Trente trames consécutives en arrêt, puis :

```
  17.0  20.5   9.1  |      5     34  |  vire a gauche
```

Un obstacle à 9,1 cm et les moteurs reçoivent une consigne de marche avant. La trame
suivante repasse en arrêt.

La cause : la décision était recalculée à chaque trame depuis la mesure brute, sans aucune
mémoire d'état. Une seule lecture aberrante du capteur central — 20,5 cm au lieu des 16
environs réels — suffisait à relâcher l'arrêt pendant 100 ms.

---

## Itération 2 — Garde-fous

### Filtre médian

Les cinq dernières mesures de chaque capteur sont conservées et la médiane est retenue.

La médiane plutôt que la moyenne : sur la séquence `5,2 → 54,5 → 4,2`, la médiane renvoie
une valeur plausible, tandis que la moyenne aurait renvoyé 21 cm, c'est-à-dire un obstacle
inexistant. Une moyenne intègre partiellement une aberration ; une médiane l'élimine
complètement.

### Seuil de panique absolu

C'est la correction la plus importante de la phase, car elle répare une limite de la
méthode elle-même et non une erreur d'implémentation.

Journal de l'itération 1 :

```
  10.5  77.3   4.6  |     19     20  |  tout droit
```

Un obstacle à 4,6 cm à droite, un autre à 10,5 cm à gauche, et la décision est « tout
droit ». Ce n'est pas un bruit de mesure : les deux distances sont sous `D_MIN`, les deux
répulsions valent donc exactement `0,0833`, et la force latérale nette est **nulle**.

Le champ de potentiel ne distingue pas « aucun obstacle » de « bloqué symétriquement des
deux côtés ». Dans les deux cas la résultante est zéro. C'est le **minimum local**, défaut
connu et documenté des méthodes de champ de potentiel, reproduit ici sur banc d'essai.

Un champ de potentiel seul ne peut pas résoudre ce cas, puisque l'information est absente
de la résultante. La correction doit venir d'un critère indépendant du calcul de forces :

```
Si une distance quelconque est inférieure à D_PANIQUE, arrêt,
quel que soit l'équilibre des forces.
```

Ce seuil résout simultanément un second défaut : les capteurs latéraux n'avaient aucun
seuil d'arrêt. Un obstacle stable à 10,5 cm du flanc gauche laissait le robot avancer
pendant 1,2 seconde. Or un châssis à chenilles de 20 cm de large ne peut pas pivoter avec
un obstacle à 10 cm de son flanc : la chenille le percute avant que le virage soit amorcé.

`D_PANIQUE` est fixé à 15 cm, valeur dérivée de la demi-largeur du châssis.

### Verrou d'arrêt

L'arrêt devient un état doté de mémoire, et non une conséquence instantanée de la mesure.
Il s'arme après un nombre donné de trames dangereuses et ne se relâche qu'après un nombre
donné de trames propres consécutives.

### Gain porté à 400

Pour permettre l'inversion de chenille.

---

## Itération 3 — Deux finitions

L'itération 2 corrigeait les trois défauts, mais les journaux ont révélé deux points
résiduels.

### L'arrêt s'armait une trame trop tard

```
   ---  77.7   4.2 |    -13     53  |  vire a gauche
   ---  77.7   4.2 |      0      0  |  ARRET - obstacle a 4 cm (droite)
```

Un obstacle à 4,2 cm reçoit une consigne moteur pendant 100 ms avant l'armement. La cause
est `TRAMES_ENTREE = 2`, choisi par prudence contre les faux arrêts dus à la diaphonie.

C'était un mauvais arbitrage. Les deux erreurs n'ont pas le même coût : un faux arrêt coûte
une fraction de seconde, un arrêt manqué coûte le châssis. **L'hystérésis d'un état de
sécurité doit être asymétrique** — entrée immédiate, sortie lente. Et le filtre médian
traitait déjà le cas que les deux trames étaient censées couvrir.

`TRAMES_ENTREE` est ramené à 1. `TRAMES_SORTIE` est porté de 5 à 8, après observation d'un
relâchement à 4/5 alors que l'obstacle était encore présent.

### `D_MIN` était devenu du code mort

```
   ---  76.9  15.2 |      0     39  |  vire a gauche
```

`D_MIN = 10` plafonnait la répulsion à 10 cm, mais `D_PANIQUE = 15` arrête le robot avant.
La plage 15–10 cm était donc inatteignable en mouvement : lorsque la fonction de répulsion
est appelée, toutes les distances valent au moins 15.

Conséquence : la correction maximale réellement atteignable n'était pas 33 comme calculé,
mais

```
400 × (1/15 − 1/60) = 400 × 0,0500 = 20
```

Le calcul initial reposait sur une plage que le seuil de sécurité rendait inaccessible.
Deux paramètres réglés séparément s'étaient révélés incompatibles sans que l'incompatibilité
apparaisse à la lecture du code.

Correction retenue : aligner `D_MIN` sur `D_PANIQUE`, ce qui supprime le code mort, et
remonter le gain à 600 pour retrouver une correction franche dans la plage qui existe
réellement, 60 à 15 cm.

Vérification que le robot ne devient pas nerveux au loin :

```
à 40 cm : 600 × (1/40 − 1/60) = 5   → consignes 15/25, doux
à 15 cm : 600 × (1/15 − 1/60) = 30  → consignes −10/50, pivot franc
```

---

## Constantes retenues

| Paramètre | Valeur | Origine |
|---|---|---|
| `D_INFLUENCE` | 60 cm | Portée au-delà de laquelle un obstacle est ignoré |
| `D_PANIQUE` | 15 cm | Dérivée de la demi-largeur du châssis |
| `D_MIN` | 15 cm | Aligné sur `D_PANIQUE` |
| `D_ARRET` | 20 cm | Seuil d'arrêt du capteur central |
| `BASE_SPEED` | 20 | Vitesse de croisière |
| `KP_OBS` | 600 | Calibré empiriquement, itération 3 |
| `POIDS_CENTRE` | 2,0 | Un obstacle de face est sur la trajectoire |
| `TRAMES_ENTREE` | 1 | Entrée immédiate en arrêt |
| `TRAMES_SORTIE` | 8 | Mesuré : 5 insuffisant |
| `FENETRE_MED` | 5 | Filtre médian |
| `TRAMES_AVANT_DEGAGEMENT` | 3 | Arrêt persistant avant manœuvre |
| `VITESSE_RECUL` | 15 | Lent, car en aveugle |
| `TRAMES_RECUL` | 8 | 0,8 s à 10 Hz |
| `VITESSE_PIVOT` | 35 | Pivot différentiel sur place |
| `TRAMES_PIVOT` | 7 | 0,7 s à 10 Hz |
| Période de boucle | 100 ms | 10 Hz |

## Validation

Profil de correction mesuré sur 360 trames, obstacle approché progressivement :

| Distance | Consignes | Correction |
|---|---|---|
| 43 cm | 23 / 16 | 3 |
| 39 cm | 25 / 14 | 5 |
| 35 cm | 27 / 12 | 7 |
| 16,6 cm | 46 / −6 | 26 |

Progressif à distance, pivot différentiel avec inversion de chenille à l'approche.

Critères vérifiés :

- Aucune consigne non nulle sous 15 cm sur 360 trames
- Blocage symétrique détecté et traité par arrêt
- Obstacle latéral seul détecté et traité par arrêt
- Hystérésis effective, aucun relâchement sur mesure aberrante isolée
- Référence en espace dégagé stable à `20 / 20`

---

# Partie 3 — Manœuvre de dégagement et intégration aux moteurs

## Ce que révèle le premier essai en déplacement

Le contrôleur moteur de remplacement a été reçu le 6 novembre. Le protocole de première
mise sous tension a été appliqué : LiPo seule sur le port PWR, mesure de la broche 5 V du
port I2C avant tout raccordement. Carte saine, adresses `0x34` et `0x68` détectées.

Le premier essai en déplacement a montré deux comportements que la simulation ne pouvait
pas révéler, parce qu'ils ne se lisent pas dans un journal de consignes.

**Le robot paraissait foncer vers un obstacle de face avant de caler.** L'explication est
dans le calcul. Face à un obstacle frontal, les deux capteurs latéraux ne voient rien :
leurs répulsions sont nulles, et seule celle du centre agit. À 40 cm elle vaut

```
600 × (1/40 − 1/60) = 5
```

soit des consignes de 25 et 15 sur une base de 20. Une inflexion à peine perceptible. Le
temps que la correction devienne franche, le robot est à 25 cm, et le seuil d'arrêt le
stoppe à 20.

**Et il ne se dégageait jamais.** Arrivé devant l'obstacle, il s'arrêtait et restait là.
C'était le comportement programmé — le champ de potentiel ne sait que dévier en avançant,
le seuil de panique ne sait que stopper — mais un robot qui s'arrête devant un obstacle ne
l'évite pas : il le constate.

## Correction 1 — pondérer le capteur central

Un obstacle de face est sur la trajectoire. C'est le plus urgent à traiter, et il pesait
pourtant autant qu'un obstacle latéral qui ne gêne personne.

`POIDS_CENTRE = 2,0` multiplie sa répulsion. À 45 cm, la correction passe de 5 à 13 :
consignes 26 et 13 au lieu de 25 et 15. Le robot s'écarte bien avant d'arriver au contact.

## Correction 2 — la manœuvre de dégagement

Quand l'arrêt persiste trois trames, l'obstacle ne partira pas de lui-même. Le robot
recule, pivote vers le côté le plus dégagé, puis repart.

La logique devient une machine à quatre états.

| État | Comportement |
|---|---|
| NORMAL | Le champ de potentiel pilote, le robot avance en déviant |
| ARRET | Un critère de sécurité est actif, consignes nulles |
| RECUL | Marche arrière à vitesse 15 pendant 0,8 s |
| PIVOT | Rotation sur place à ±35 pendant 0,7 s |

Le côté du pivot est choisi au moment de l'arrêt, en comparant les deux capteurs
latéraux : on tourne vers celui qui voit le plus loin.

**Les deux manœuvres ignorent les capteurs pendant leur durée.** C'est délibéré. Une
manœuvre de dégagement interrompue à mi-course laisse le robot exactement dans la
situation qu'elle devait résoudre, et il recommencerait indéfiniment.

**Limite assumée : aucun capteur à l'arrière.** Le recul se fait en aveugle. Il est donc
volontairement court et lent — assez pour dégager le châssis, pas assez pour aller
percuter ce qui se trouve derrière. Un capteur arrière est la condition pour l'allonger,
et ce sera le moment de reconsidérer ces deux constantes.

## Séquence obtenue

Approche frontale simulée, puis vérifiée en déplacement :

```
tout droit                      20 /  20
vire a droite                   26 /  13
vire a droite                   40 /   0
ARRET - obstacle de face         0 /   0
DEGAGEMENT - recul 1/8         -15 / -15
   ...
DEGAGEMENT - recul 8/8         -15 / -15
DEGAGEMENT - pivot droite 1/7   35 / -35
   ...
DEGAGEMENT - pivot droite 7/7   35 / -35
tout droit                      20 /  20
```

## Un correctif retiré

Une coupure du connecteur de la LiPo en cours d'essai a fait perdre à la Hiwonder ses
registres de configuration, volatils. Au retour du courant, la carte interprétait les
consignes autrement et les moteurs tournaient sans commande.

Une reconfiguration **périodique** a été essayée : réécrire `MOTOR_TYPE` toutes les deux
secondes pour rendre toute micro-coupure invisible. Elle a dégradé le comportement dans
les deux modes et a été retirée.

La cause est claire rétrospectivement. Réécrire le registre de type moteur pendant que
les moteurs tournent demande au contrôleur de reconfigurer son étage de puissance en
pleine marche. Rien ne garantit qu'il encaisse cette opération proprement. Le correctif
introduisait une perturbation régulière pour compenser une perturbation occasionnelle.

Seule la reconfiguration **réactive** a été conservée : sur échec avéré d'écriture I2C,
le script reconfigure la carte avant la commande suivante. Et le vrai correctif d'une
alimentation intermittente reste le connecteur, pas le logiciel.

**Leçon :** un correctif logiciel qui compense un défaut matériel doit être évalué sur
son effet global, pas seulement sur le symptôme qu'il vise. Celui-ci corrigeait un
problème rare en en créant un permanent.

---

# Partie 4 — Sélecteur de mode à la manette

## Objet

Jusqu'ici, la téléopération et l'évitement autonome étaient deux scripts distincts, lancés
séparément. Deux démonstrations, pas un système.

Le sélecteur de mode les réunit : un bouton de la manette choisit qui commande les
moteurs, sans rien relancer.

| Bouton | Mode | Qui commande |
|---|---|---|
| A | Téléopération | Le joystick, relayé tel quel |
| B | Autonome | La logique d'évitement, sur le Raspberry Pi |
| Y | Arrêt | Personne, consignes nulles |

## Choix de conception

**Trois boutons distincts plutôt qu'une bascule sur un seul.** Avec une bascule, l'état
demandé dépend de l'historique : une pression non enregistrée inverse la signification de
toutes les suivantes, et on ne le découvre qu'au moment où le robot part dans le mauvais
mode. Avec trois boutons, l'état demandé est toujours explicite.

**Détection sur front montant.** Sans cela, un appui maintenu de 200 ms réémettrait le
changement de mode dix fois de suite.

**Mode arrêt au démarrage.** Rien ne bouge avant une action délibérée.

**Un seul format de trame.** La trame passe de `L,R` à `M,L,R`. En mode arrêt et en mode
autonome, L et R valent toujours 0 — c'est le Raspberry Pi qui calcule les consignes en
autonome. Garder le champ évite d'avoir deux formats à analyser.

## Sécurités

Deux replis indépendants ramènent le robot à l'arrêt.

**Côté ESP32 :** toute déconnexion de la manette force le mode arrêt et réémet
périodiquement `0,0,0`, pour que l'ordre passe même si une trame se perd.

**Côté Raspberry Pi :** si aucune trame valide n'arrive pendant 300 ms, repli en arrêt.
L'absence de nouvelle n'est jamais interprétée comme « continue comme avant ». La manette
ou l'ESP32 peuvent se taire sans prévenir.

Un changement de mode arrête d'abord les moteurs et réinitialise le verrou d'évitement :
au retour en autonome, l'état d'arrêt ne doit pas être hérité d'une situation qui n'existe
plus.

## Dérive du joystick

Au repos, le robot tournait sur lui-même de façon intermittente. Les consignes affichées
étaient `G = 19, D = -19`, parfaitement opposées — une rotation pure, donc `linear = 0` et
`angular = -19`.

La conversion va de ±32768 vers ±100, ce qui situe la valeur brute à

```
19 × 32768 / 100 ≈ 6226
```

pour une zone morte de 6000. Le joystick reposait à 226 unités au-delà du seuil, soit 3 %
de dépassement.

Ce n'est pas un défaut de code : le point de repos d'un stick Xbox dérive avec l'usage, la
température et la façon dont on le relâche. La calibration, elle, n'avait lieu qu'une
fois, à la connexion de la manette.

Deux corrections. La zone morte passe de 6000 à 9000, ce qui couvre la dérive observée
avec une marge. Et le bouton Y déclenche désormais une **recalibration** en plus de
l'arrêt : c'est précisément le moment où le robot est immobile et le joystick censé être
libre. Une calibration faite une seule fois finit par mentir ; une calibration qu'on peut
refaire d'un bouton, non.

## Écriture de la consigne moteur

Une première version n'écrivait la consigne I2C **que lorsqu'elle changeait**, pour ne pas
saturer le bus. Les moteurs ne tournaient pas.

La consigne est maintenant réécrite toutes les 50 ms, comme le fait `test_motors.py`, qui
fonctionne. Le registre de vitesse de la Hiwonder se réécrit sans coût notable, et une
écriture perdue est rattrapée au cycle suivant.

**Leçon :** une optimisation qui supprime la redondance supprime aussi la tolérance aux
pannes. Sur une commande d'actionneur, la redondance n'est pas du gaspillage.

Un second défaut tenait au masque. Le registre attend des octets de 0 à 255, et une
consigne négative — marche arrière, ou chenille inversée en évitement — sort de cette
plage. `test_motors.py` appliquait `& 0xFF`, le dispatcher non.

---

## Limite identifiée, non corrigée

Journal de l'itération 3, lignes 156 à 179 : le capteur gauche reste entre 16 et 19 cm
pendant 2,4 secondes et les consignes tiennent `46 / −6` sans varier.

Sur le robot en déplacement, cela signifie un pivot sur place maintenu. Le champ de
potentiel ne possède aucune mémoire de cap : il ne réagit qu'à la mesure instantanée et ne
sait pas qu'il a déjà tourné.

Face à un mur parallèle à sa trajectoire, le robot pivotera jusqu'au dégagement du capteur,
repartira, se rapprochera à nouveau, et recommencera — une oscillation le long du mur.

Ce comportement n'est pas corrigé à ce stade, l'évitement d'obstacles isolés étant le
périmètre de la phase. L'outil nécessaire existe déjà : l'estimation de cap issue de la
fusion inertielle de la Phase 3. Un terme pénalisant l'écart au cap visé transformerait le
pivot réactif en évitement orienté. Cette intégration appartient à la Phase 5, où la notion
de cap visé existe enfin.

---

## Ce que cette phase a démontré méthodologiquement

Les deux défauts les plus significatifs n'étaient pas des erreurs de code et n'auraient été
détectés par aucun test unitaire.

Le premier — le minimum local — est une **limite mathématique de la méthode choisie**. Le
code implémentait correctement le champ de potentiel ; c'est le champ de potentiel qui ne
contient pas l'information nécessaire au cas symétrique. Sa correction a demandé d'ajouter
un critère extérieur à la méthode, non de corriger la méthode.

Le second — `D_MIN` inatteignable — est une **interaction entre deux paramètres** réglés
séparément à des moments différents, chacun correct isolément. Il ne s'est manifesté par
aucune anomalie de comportement : le robot se comportait raisonnablement, simplement avec
une correction maximale de 20 au lieu des 33 documentés. Un écart entre le comportement
réel et le comportement supposé, invisible sans le calcul explicite de la borne.

Dans les deux cas, l'identification est venue de la lecture attentive de journaux de
plusieurs centaines de trames, et non de l'inspection du code. Le mode simulation, imposé
par une panne matérielle, est ce qui a rendu cette lecture possible : un robot en mouvement
n'aurait montré qu'une collision, sans indiquer laquelle des causes possibles était en jeu.

Le passage aux moteurs a ensuite révélé ce que la simulation ne pouvait pas voir, et la
distinction mérite d'être posée. La simulation valide la **décision** : elle montre ce que
le robot déciderait, trame par trame, et c'est là qu'on attrape un calcul faux ou une borne
inatteignable. Le déplacement valide la **suffisance** de cette décision : une correction
peut être correctement calculée et malgré tout arriver trop tard, ou laisser le robot dans
une impasse dont rien ne le sort. Aucun des deux essais ne remplace l'autre.

Enfin, la reconfiguration périodique retirée en Partie 3 illustre un piège distinct : un
correctif logiciel visant un défaut matériel doit être jugé sur son effet global, pas sur
le symptôme qu'il vise. Celui-ci supprimait un problème rare en en créant un permanent.

---

## Scripts associés

| Fichier | Rôle |
|---|---|
| `scripts/phase4/test_hcsr04_triple.py` | Validation matérielle des trois capteurs |
| `scripts/phase4/evitement.py` | Module : constantes, filtrage, machine d'états |
| `scripts/phase4/obstacle_logic_test.py` | Réglage en simulation, sans moteurs |
| `scripts/phase4/mode_receiver.py` | Sélecteur de mode, programme principal |
| `firmware/esp32/src/main.cpp` | Manette, sélection du mode, affichage, UART |

Les constantes ne vivent qu'à un seul endroit, dans `evitement.py`. Le réglage trouvé en
simulation est donc automatiquement celui qui pilote le robot : deux copies finiraient par
diverger, et on ne saurait plus laquelle tourne.

`evitement.py` est un module, jamais exécuté seul. Il doit se trouver dans le même dossier
que les deux scripts qui l'importent.

## Suite

La Phase 5 donne un but au robot : atteindre des coordonnées cibles. C'est là que les trois
phases précédentes se composent — l'odométrie de la Phase 3 dit où il est, un cap visé dit
où aller, et l'évitement de la Phase 4 s'intercale en priorité quand quelque chose bloque.

C'est aussi là que se traite la limite décrite ci-dessus. Avec un cap visé, l'évitement
devient une déviation autour d'un objectif plutôt qu'une réaction sans mémoire, et le robot
reprend sa route au lieu de rebondir le long d'une paroi.
