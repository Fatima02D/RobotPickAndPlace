# Problèmes & Solutions

**Projet :** Robot Mobile Autonome Pick & Place
**Auteure :** Saida Fatimatou Zahraa Diouf

---

## Philosophie

En ingénierie, un problème n'est pas un échec. C'est une donnée. Chaque obstacle
rencontré ici a mené à une meilleure décision.

---

# Partie A — Plateforme 2WD, plaque en bois (Janvier 2026)

## A1 — Moteurs immobiles au départ

**Sévérité :** critique. **Statut :** résolu.

Le code se téléversait correctement et le moniteur série affichait les messages
attendus, mais aucun moteur ne tournait et aucun bruit n'était audible.

Quatre hypothèses ont été testées dans l'ordre :

| Hypothèse | Test | Résultat |
|---|---|---|
| Problème logiciel | Code simplifié | Écartée |
| Pins PWM incorrectes | digitalWrite au lieu d'analogWrite | Écartée |
| Alimentation moteur absente | Tension mesurée sur Vmotor : 0V | Cause racine |
| Masse non commune | Pas de continuité Arduino/L298N | Cause secondaire |

**Solution :** connecter la batterie 7,4V sur le L298N et ajouter un fil de masse
commune entre l'Arduino et le driver.

**Leçon :** l'alimentation logique et l'alimentation puissance sont deux circuits
distincts, mais ils doivent partager la même masse. Sans référence commune, les signaux
PWM n'ont aucune signification pour le driver.

---

## A2 — Confusion entre fils moteur et fils encodeur

**Sévérité :** modérée. **Statut :** résolu.

Tentative de brancher les fils Hall de l'encodeur sur le driver moteur.

Un moteur à courant continu avec encodeur compte six fils, répartis en deux circuits :

```
Puissance (vers le driver) :
  Rouge  — Moteur+
  Noir   — Moteur-

Encodeur (vers le microcontrôleur) :
  VCC    — 3,3V ou 5V
  GND    — masse
  Hall A — signal d'impulsions
  Hall B — signal d'impulsions, donne le sens de rotation
```

**Leçon :** puissance et mesure sont toujours deux circuits séparés.

---

## A3 — Canal B du L298N défectueux

**Sévérité :** haute. **Statut :** non résolvable, composant grillé.

Le moteur gauche fonctionnait, le droit restait immobile.

Diagnostic par permutation : les deux moteurs ont été inversés physiquement. Le moteur
précédemment immobile a fonctionné sur le canal A, et le moteur fonctionnel est resté
immobile sur le canal B. Le canal B du driver est donc défectueux.

**Décision :** migration vers un châssis Hiwonder à chenilles avec driver intégré.

---

## A4 — Châssis en bois trop flexible

**Sévérité :** haute. **Statut :** résolu par migration.

Flexion de 2 à 3 mm au centre sous une charge de 200 g, avec vibrations visibles aux
démarrages.

| Matériau | Module de Young |
|---|---|
| MDF | environ 4 000 MPa |
| Aluminium | environ 69 000 MPa |

Le bois est environ dix-sept fois moins rigide que le métal. Le serrage des entretoises
n'a apporté qu'une amélioration inférieure à 10 %, et la redistribution des masses a
ramené la flexion à 1-2 mm sans suffire.

**Conclusion :** non résolvable sans changement de matériau.

---

## A5 — Roue folle non déterministe

**Sévérité :** critique. **Statut :** résolu par migration.

Déviation moyenne de 13,4 cm sur 2 mètres, non reproductible d'un essai à l'autre.

| Essai | Déviation sur 2 m |
|---|---|
| 1 | 15 cm à gauche |
| 2 | 8 cm à droite |
| 3 | 12 cm à gauche |
| 4 | 3 cm à droite |
| 5 | 18 cm à gauche |

Trois tentatives de compensation logicielle ont échoué : offset PWM fixe (13 cm vers
8 cm), courbe PWM/vitesse (environ 5 cm), PID impossible sans encodeurs.

**Pourquoi c'est insoluble logiciellement :** la friction de la roue folle varie à chaque
instant et n'est pas observable. Toute compensation basée sur la déviation mesurée arrive
trop tard.

**Solution :** le skid steering par chenilles élimine la roue folle.

---

## A6 — Moteurs non synchronisés

**Sévérité :** haute. **Statut :** résolu par boucle fermée en Phase 3.

À consigne PWM identique, un moteur tournait environ 5 à 6 % plus vite que l'autre.
Cause : tolérance normale de fabrication des moteurs à courant continu.

---

## A7 — Bruit électrique et parasites

**Sévérité :** modérée. **Statut :** atténué.

Lectures d'encodeurs erratiques et redémarrages spontanés de l'Arduino, causés par
l'interférence électromagnétique des moteurs.

**Solutions :** séparation physique des câbles puissance et signal d'au moins 3 cm,
condensateurs de découplage 100 uF sur l'alimentation moteur, alimentation logique
séparée pendant les essais.

---

## Décision de migration

| Catégorie | Nombre de problèmes |
|---|---|
| Résolvables logiciellement | 2 sur 7 (29 %) |
| Nécessitant un changement matériel | 5 sur 7 (71 %) |

Cinq problèmes sur sept exigeaient un changement de plateforme. La migration vers un
châssis à chenilles était justifiée par les données, non par préférence.

---

# Partie B — Plateforme à chenilles (Avril-Juin 2026)

## B1 — Connecteur LiPo incompatible

Le connecteur XT30 de la batterie ne correspond pas au port PWR du module Hiwonder
(JST). Adaptateur Deans vers JST, inclus avec le chargeur.

## B2 — Carte SD incompatible

Le Raspberry Pi 4B exige une micro SD. Une SanDisk 32 GB a été achetée.

## B3 — SSH non fonctionnel après le premier flash

Le RPi démarrait mais refusait toutes les connexions SSH. La case d'activation n'avait
pas été correctement cochée dans Raspberry Pi Imager. Solution : reflasher en vérifiant
visuellement l'activation.

Distinction utile au diagnostic : `Connection refused` signifie que le RPi répond mais
que SSH est fermé, tandis que `Connection timed out` signifie qu'il ne répond pas.

## B4 — Nom d'hôte non résolvable

```
ssh: Could not resolve hostname indigowing.local
```

L'ordinateur et le RPi se trouvaient sur des réseaux différents. Solution : utiliser le
partage de connexion mobile comme réseau commun.

## B5 et B11 — Avertissement de changement de clé SSH

```
WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!
Host key verification failed.
```

Chaque reflash de la micro SD génère une nouvelle clé SSH sur le RPi, alors que
l'ordinateur conserve l'ancienne dans son fichier `known_hosts`. Ce n'est pas une
attaque : le RPi a simplement changé d'identité.

```bash
ssh-keygen -R indigowing.local
ssh indigozafa@indigowing.local
```

À refaire après chaque reflash.

## B6 — Court-circuit du Raspberry Pi

Le RPi s'éteignait dès qu'on branchait certains fils sur le GPIO. La Powerbank et la
sortie 5V du module Hiwonder l'alimentaient simultanément.

**Règle établie :** une seule source d'alimentation par composant. La Powerbank alimente
le RPi, et rien d'autre ne doit injecter de tension sur son rail 5V.

Méthode de diagnostic retenue : brancher un fil à la fois, en commençant par la masse,
pour isoler la connexion fautive.

## B7 — Signal ECHO du HC-SR04 incompatible

Le HC-SR04 émet 5V sur sa broche ECHO alors que les GPIO du RPi acceptent 3,3V au
maximum. Un diviseur résistif est obligatoire :

```
ECHO (5V) ---- 1 kOhm ---- GPIO du RPi
                    |
                 2 kOhm
                    |
                   GND

5V x (2k / 3k) = 3,33V
```

## B8 — I2C non activé

```
Error: Could not open file /dev/i2c-1
```

L'I2C est désactivé par défaut sur Raspberry Pi OS et doit être réactivé après chaque
flash.

```bash
sudo raspi-config
# Interface Options -> I2C -> Yes
sudo reboot
i2cdetect -y 1
```

## B9 — Registres I2C incorrects

Le script s'exécutait sans erreur mais les moteurs ne bougeaient pas. Le registre 0x01
avait été utilisé au lieu des registres réels du module.

Registres corrects, trouvés dans la documentation officielle Hiwonder :

```python
I2C_ADDR                    = 0x34
MOTOR_TYPE_ADDR             = 20
MOTOR_ENCODER_POLARITY_ADDR = 21
MOTOR_FIXED_SPEED_ADDR      = 51
```

## B10 — Fils moteurs débranchés

Les moteurs émettaient un bruit sans tourner : les connecteurs JST s'étaient détachés
des ports M1 et M2. Reconnecter fermement a suffi.

---

# Partie C — Phase 2, liaison ESP32 vers RPi (Juin 2026)

## C1 — GPIO43 et GPIO44 bloquent la communication UART

Avec Serial2 configuré sur ces broches, aucune donnée n'arrivait jamais sur le RPi, pas
même du bruit.

**Cause :** GPIO43 et GPIO44 sont les broches UART0 natives de l'ESP32-S3, déjà réservées
par le système même quand le port série standard passe par l'USB. La matrice GPIO ne peut
pas surcharger cette connexion fixe.

**Solution :** revenir à GPIO17 pour l'émission et GPIO27 pour la réception.

**Leçon :** sur ESP32-S3, vérifier quelles broches sont liées à des périphériques natifs
avant de les assigner.

## C2 — Données UART corrompues

```
Erreur: 'utf-8' codec can't decode byte 0xfe in position 1
```

La masse n'était pas connectée entre l'ESP32 et le RPi. Sans référence commune, les
niveaux logiques dérivent et les bits sont lus de travers.

**Leçon :** même cause qu'en Phase 1 avec les moteurs. La masse commune est la base de
toute communication, quel que soit le protocole.

## C3 — Joystick non centré au repos

Le robot avançait ou tournait sans qu'on touche la manette.

L'affichage des valeurs brutes a montré que le joystick au repos se stabilise autour de
200-300 sur l'axe vertical et de -1488 sur l'axe horizontal, avec des pics transitoires
beaucoup plus élevés au moment de la connexion.

**Solution :** zone morte portée à 6000 sur la plage brute de 65536, soit 9,2 % de la
course. La zone morte doit être appliquée sur chaque axe avant le mélange des consignes :
appliquée après, un résidu sur l'axe horizontal survit au calcul et fait pivoter le robot
en continu.

## C4 — Confusion entre code de test et code réel

Le robot exécutait une boucle automatique de mouvements sans manette connectée.

Un code de test fixe, écrit pour isoler un problème de communication, était resté flashé
sur l'ESP32 à la place du vrai code de lecture manette.

**Leçon :** toujours confirmer quel code est actuellement sur le microcontrôleur avant
d'interpréter un comportement comme un bug, surtout après une session de débogage avec
plusieurs versions testées.

## C5 — Masquage de bits suspecté à tort

Le robot semblait toujours avancer ou tourner à droite quelle que soit la direction du
joystick. L'hypothèse testée portait sur `left & 0xFF` appliqué à une valeur négative.

Un test manuel direct avec des valeurs négatives explicites, sans masquage, a fonctionné
correctement dans les quatre directions. Le masquage n'était donc pas la cause : le
problème venait du code de test resté actif (C4).

**Leçon :** isoler chaque variable séparément avant de conclure. Plusieurs problèmes
peuvent se chevaucher et donner l'illusion qu'une correction a réglé le souci.

## C6 — Dépassement de capacité sur int16_t

Après correction de la zone morte et du code de test, le robot répondait encore de façon
incohérente : un seul axe semblait contrôler à la fois la vitesse et la direction.

**Cause :** les valeurs brutes étaient stockées en int16_t. Après soustraction du centre
de calibration, certaines dépassaient la plage représentable (-32768 à 32767), provoquant
un retournement qui inversait le signe de façon imprévisible.

**Solution :** calibration automatique du centre au démarrage, moyennée sur 30
échantillons, et tous les calculs intermédiaires passés en int32_t.

**Leçon :** utiliser un type avec assez de marge pour les calculs intermédiaires,
particulièrement lors du recentrage de valeurs analogiques près des limites du type.

## C7 — Erreur de compilation avr/eeprom.h

```
fatal error: avr/eeprom.h: No such file or directory
```

L'ajout de TFT_eSPI a entraîné l'inclusion automatique d'une librairie conçue pour les
microcontrôleurs AVR, incompatible avec l'ESP32.

**Solution :** `lib_ldf_mode = chain+` dans platformio.ini, puis `pio run --target clean`.

**Leçon :** une erreur venant d'une librairie qu'on n'a pas demandée signale une
résolution de dépendances trop permissive.

## C8 — Sortie 5V du module Hiwonder inexploitable

L'ESP32 ne démarrait pas lorsqu'il était alimenté par la sortie 5V du module Hiwonder.

Diagnostic : la tension d'entrée au port PWR était normale (environ 7V), mais la sortie
5V régulée mesurait 2,7V, stable, même sans aucune charge branchée. Une sortie régulée
anormalement basse à vide indique un régulateur défaillant ou sous-dimensionné.

**État :** non résolu. L'ESP32 reste alimenté par USB. Un convertisseur abaisseur dédié
entre la LiPo et l'ESP32 est nécessaire pour l'autonomie complète.

**Leçon :** ne jamais supposer qu'une sortie régulée existante a la capacité en courant
suffisante pour une nouvelle charge. Mesurer sous charge réelle avant de bâtir une
architecture d'alimentation autour d'elle.

## C9 — Latence croissante entre commande et mouvement

Les chiffres changeaient en temps réel dans le moniteur série de l'ESP32, mais les
moteurs réagissaient avec dix secondes de retard.

**Cause :** l'ESP32 émet à 50 Hz, plus vite que le RPi ne traite chaque trame (écriture
I2C, affichage SSH). Le tampon série accumulait les trames, et le script lisait des
commandes vieilles de plusieurs secondes.

**Solution :** vider complètement le tampon à chaque itération et ne conserver que la
trame la plus récente.

## C10 — Commandes d'arrêt perdues

Le terminal affichait des consignes nulles mais les moteurs continuaient de tourner.
L'écriture I2C échouait par intermittence, et le module conservait la dernière consigne
valide reçue.

**Solution :** deux mécanismes. La commande d'arrêt est réémise jusqu'à confirmation
d'écriture, et un dispositif de repli arrête les moteurs en l'absence de trame pendant
plus de 200 ms.

**Leçon :** une commande d'arrêt exige un traitement particulier. Un système mobile dont
l'immobilisation dépend d'une trame susceptible d'être perdue n'est pas sûr.

---

# Partie D — Phase 3, odométrie (Juillet 2026)

## D1 — Rotation infinie du robot

```
Rotation : -1452.4 deg
```

Le gyroscope MPU6050 retourne des valeurs négatives pour une rotation vers la gauche sur
ce montage. La condition d'arrêt vérifiait `while angle_deg < CUTOFF_DEG`, toujours vraie
puisque l'angle descendait vers -80 au lieu de monter vers +80.

**Solution :** `while abs(angle_deg) < CUTOFF_DEG`.

**Leçon :** vérifier le signe des valeurs brutes d'un capteur d'orientation avant
d'écrire une condition d'arrêt. La convention dépend du montage physique, pas du code.

## D2 — Robot qui tourne en avançant pendant le parcours en carré

Les côtés du carré n'étaient pas droits : le robot déviait continuellement.

**Cause :** la fonction d'avance ne corrigeait le cap qu'au démarrage, pas à chaque
cycle. L'enchaînement avance/rotation mélangeait les deux mouvements.

**Solution :** correction du cap recalculée à chaque itération pendant toute la durée du
déplacement, fonctions d'avance et de rotation complètement séparées, et pause de
stabilisation de 0,5 s entre chaque mouvement.

## D3 — Valeur théorique METRES_PAR_PULSE fausse d'un facteur 3,8

La valeur calculée à partir des spécifications moteur était de 2,36e-5 m par impulsion.
La mesure au sol, sur 90 cm et quatre essais, a donné 9,01e-5 m par impulsion, puis
1,05e-4 avec la rampe de démarrage.

Un écart de ce facteur ne s'explique pas par le patinage, qui fait perdre 10 à 30 % de
distance, pas 280 %. Les spécifications héritées ne correspondaient pas aux moteurs réels
du châssis.

**Leçon :** ne jamais supposer qu'une constante physique héritée d'une documentation est
correcte pour un composant spécifique. La mesure directe est obligatoire.

## D4 — Déséquilibre moteur révélé comme artefact de saturation

La Partie 1 avait mesuré un déséquilibre de 4 % entre les moteurs à la consigne 50, et
appliqué un coefficient correcteur K_RIGHT = 0,9639.

Un profil consigne-vitesse ultérieur a révélé que les moteurs saturent à partir de la
consigne 40 : la consigne 40 et la consigne 100 produisent la même vitesse. Les mesures
de la Partie 1 avaient donc été faites en pleine saturation, où deux points ne sont pas
comparables.

En régime non saturé (consigne 20), le même test répété quatre fois donne un écart dont
le signe change d'un essai à l'autre : du bruit, pas un biais. Le module assure lui-même
une régulation de vitesse en boucle fermée.

**Solution :** K_RIGHT fixé à 1,0, neutralisé mais conservé dans le code avec un
commentaire expliquant la décision. Plage de consigne exploitable : 10 à 30.

**Leçon :** une correction adoptée sur la base de mesures doit être remise en question si
de nouvelles mesures montrent que le phénomène corrigé était un artefact du protocole.

## D5 — Dérive résiduelle par patinage des chenilles

Même avec l'asservissement actif, le robot ne roule pas toujours parfaitement droit.

L'asservissement corrige les écarts de cap, c'est-à-dire la rotation du châssis. Il ne
corrige pas le glissement latéral pur : si les deux chenilles glissent du même côté
simultanément, le châssis ne tourne pas et le gyroscope ne détecte rien.

Résultats obtenus avec KP = 0,7 : environ 1 cm de déviation sur 82 cm en ligne droite,
13,3 cm d'erreur de bouclage sur un carré de 4 m (3,3 %), environ 2 degrés d'erreur de
cap après quatre rotations.

Ces valeurs sont dans la plage attendue pour un chenillard sans référence externe. La
réponse structurelle est l'ajout d'une référence externe (caméra, LiDAR) en Phase 5.

---

# Partie E — Phase 4, capteurs ultrason (Août 2026)

## E1 — Surtension et court-circuit

Les fils chauffaient immédiatement à la connexion et le convertisseur n'affichait plus de
valeur stable.

**Deux causes simultanées :** la batterie délivrait 7,4V sans régulation suffisante, et un
potentiomètre classique avait été utilisé à la place d'un convertisseur de tension. Un
potentiomètre est un diviseur résistif : il dissipe le courant excessif en chaleur au lieu
de le réguler.

**Solution :** identification correcte du composant comme convertisseur buck LM2596,
coupure immédiate de l'alimentation, et réglage à exactement 5V mesuré au multimètre avant
toute connexion.

**Leçon :** ne jamais connecter une charge sur un convertisseur sans avoir mesuré et
confirmé sa tension de sortie. Un potentiomètre n'est pas un régulateur.

## E2 — Un capteur détruit par la surtension

Après résolution de E1, les fils chauffaient encore dès qu'un capteur spécifique était
branché, même avec une alimentation correcte.

Ce capteur avait subi un court-circuit interne lors de l'exposition initiale à 7,4V. Ses
composants internes étaient fondus, et il se comportait comme un court-circuit direct
entre VCC et GND.

**Méthode de diagnostic :** branchement des capteurs un par un avec observation de la
température des fils. Le capteur défectueux a été identifié précisément et remplacé.

**Leçon :** après tout incident de surtension, tester chaque composant individuellement
avant de reconstituer le circuit. Un composant apparemment intact peut avoir subi des
dommages internes invisibles.

## E3 — Saturation de la breadboard pour les masses

Les colonnes verticales de cinq trous se saturaient rapidement : six fils de masse
devaient se connecter (convertisseur, RPi, trois capteurs, diviseurs).

**Solution :** utiliser les longues lignes horizontales de la breadboard comme bus de
masse commun. Cette autoroute de masse garantit que tous les composants partagent le même
potentiel de référence, condition obligatoire pour que les signaux ECHO soient interprétés
correctement.

## E4 — Mini breadboards à l'origine de courts-circuits

Courts-circuits aléatoires et intermittents, difficiles à localiser malgré un branchement
apparemment correct. Les mini breadboards utilisées comme points de connexion
intermédiaires avaient des contacts internes défectueux créant des ponts involontaires.

**Solution :** mini breadboards retirées, connexions refaites sur la breadboard principale
avec ses rails horizontaux pour la distribution.

## E5 — Conflits de broches GPIO

GPIO10, initialement choisi pour un signal ECHO, entre en conflit avec SPI_MOSI.

**Branchements définitifs validés :**

| Capteur | TRIG | ECHO |
|---|---|---|
| Gauche | GPIO23 (Pin 16) | GPIO24 (Pin 18) |
| Centre | GPIO17 (Pin 11) | GPIO27 (Pin 13) |
| Droite | GPIO22 (Pin 15) | GPIO26 (Pin 37) |

## E6 — Alimentation des capteurs

Tentative d'alimenter les trois capteurs par le LM2596 depuis la batterie, abandonnée :
les fils jumper standard, calibrés pour 1 A, ne supportent pas le courant d'appel d'un
convertisseur alimenté par une LiPo 50C.

**Solution :** les trois capteurs consomment ensemble environ 45 mA, très en dessous de ce
que le rail 5V du RPi peut fournir. Ils sont alimentés directement par le Pin 2 (5V) et un
pin GND du RPi, ce qui garantit aussi la masse commune avec le reste du montage.

---

## Leçons transversales

**La masse commune est le point de défaillance dominant de ce montage.** Elle a provoqué
l'échec de la liaison UART, puis celui du bus I2C, puis la perte de commandes d'arrêt.
Dans les trois cas, le symptôme initial pointait vers une cause logicielle alors que le
diagnostic réel était électrique. Une masse défectueuse ne produit pas une panne franche
mais un comportement intermittent, ce qui la rend particulièrement coûteuse à
diagnostiquer.

**L'étiquette d'une broche ne suffit pas.** Une broche disponible sur le brochage peut
être liée à un périphérique natif ou servir au démarrage. Consulter le schéma de la carte
précède son câblage.

**Isoler une variable à la fois.** Plusieurs problèmes peuvent se chevaucher et donner
l'illusion qu'une correction a réglé le souci alors qu'un autre problème était la vraie
cause.

**Mesurer plutôt que supposer.** Une constante héritée d'une documentation, une tension
annoncée sur une fiche technique, un déséquilibre mesuré hors de la plage utile : chacune
de ces valeurs s'est révélée fausse pour ce montage spécifique.

**Une commande d'arrêt n'est pas une commande ordinaire.** Elle exige réémission jusqu'à
confirmation et repli sur temporisation.
