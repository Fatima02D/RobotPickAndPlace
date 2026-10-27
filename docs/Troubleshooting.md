# Problèmes & Solutions

**Projet :** Robot Mobile Autonome Pick & Place
**Auteure :** Saida Fatimatou Zahraa Diouf

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

# Partie F — Phase 4, logique d'évitement (Octobre 2026)

## F1 — Destruction du contrôleur moteur Hiwonder par régulateur défaillant

L'adresse I2C `0x34` du contrôleur moteur, détectée et fonctionnelle depuis la Phase 1, a
cessé d'apparaître au balayage du bus. Le MPU6050 restait visible à `0x68`, ce qui excluait
une panne globale du bus.

**Diagnostic, étape par étape.**

La LiPo était acheminée vers le Hiwonder à travers deux plaques d'essai successives.
Première correction : raccordement direct de la batterie au port PWR de la carte par un
adaptateur Deans vers JST.

Mesure ensuite effectuée sur le port I2C de la carte, batterie seule raccordée, rien
d'autre connecté :

```
broche 5V du port I2C ↔ GND : 7 V
```

Une broche étiquetée 5 V délivrant la tension brute de la batterie signifie une seule
chose : le régulateur interne de la carte est détruit, entrée court-circuitée sur sortie.

Les lignes de signal, mesurées séparément, étaient saines :

```
SCL ↔ GND : 200 mV
SDA ↔ GND : 195 mV
```

Vérification finale avec SDA, SCL et GND seuls raccordés, la broche 5 V laissée libre :

```
i2cdetect -y 1  →  les 112 adresses répondent
```

Cent douze périphériques n'existent pas. C'est la signature d'une ligne SDA bloquée à
l'état bas : chaque adresse interrogée paraît acquittée. Hiwonder retiré, le balayage
redevient propre.

**Verdict :** contrôleur I2C de la carte détruit, carte irrécupérable.

**Portée rétrospective.** Cette défaillance explique également la destruction du premier
Raspberry Pi, attribuée jusque-là à un court-circuit de câblage (B6). Une broche annoncée à
5 V qui délivre 7,4 V alimentait les entrées GPIO limitées à 3,3 V.

**Leçon :** une broche d'alimentation d'un module tiers se mesure avant tout raccordement,
même et surtout lorsqu'elle est étiquetée. L'étiquette décrit l'intention du concepteur,
pas l'état du composant. Sur la carte de remplacement, mesurer la broche 5 V du port I2C
avant la première connexion : 7 V signifie carte défectueuse à l'arrivée, à retourner.

**Règles permanentes établies à la suite de cet incident :**

- La broche 5 V du port I2C du Hiwonder n'est raccordée à rien. Trois fils seulement :
  SDA, SCL, GND.
- La LiPo rejoint le port PWR du Hiwonder en direct, jamais à travers une plaque d'essai.
- Le VCC du MPU6050 reste sur la broche 1 du RPi (3,3 V), jamais sur le convertisseur.
- La sortie négative du convertisseur rejoint le rail de masse commune.
- Le RPi est alimenté par la batterie externe via USB-C, jamais par les broches GPIO.
- Le convertisseur est réglé à 5,0 V, mesuré à vide, avant tout raccordement.

## F2 — Erreur `GPIO not allocated` persistante

Le script de test des capteurs à ultrasons, écrit avec `RPi.GPIO`, échouait au lancement :

```
lgpio.error: 'GPIO not allocated'
```

Sous Raspberry Pi OS Bookworm, `RPi.GPIO` passe par une couche de compatibilité `lgpio`
qui ne libère pas correctement les broches lorsqu'un script se termine anormalement. Le
descripteur survit à l'arrêt du processus.

**Solution :** réécriture avec `gpiozero.DistanceSensor`, bibliothèque native de Bookworm.
Elle gère le chronométrage des impulsions en interne et libère les broches de manière
fiable.

**Leçon :** sur Bookworm, `RPi.GPIO` est une bibliothèque héritée émulée. Pour tout nouveau
code, `gpiozero` est le choix par défaut.

## F3 — Erreur `GPIO busy` survivant au redémarrage

Après la réécriture avec `gpiozero`, l'erreur persistait sous une autre forme :

```
lgpio.error: 'GPIO busy'
```

sur GPIO24, la ligne ECHO du capteur gauche. Un redémarrage complet n'y changeait rien, ce
qui excluait un processus résiduel. `gpioinfo | grep -i used` ne retournait rien.

**Cause :** une ligne ajoutée dans `/boot/firmware/config.txt` plusieurs semaines
auparavant, lors du dépannage du bus I2C.

```
dtoverlay=i2c-gpio,bus=3,i2c_gpio_sda=23,i2c_gpio_scl=24
```

Cet overlay créait un bus I2C logiciel sur GPIO23 et GPIO24, exactement les deux broches du
capteur gauche. Le noyau réservait ces lignes au démarrage, avant que `gpiozero` ne puisse
les demander. `gpioinfo` ne l'affichait pas parce que l'overlay réserve les lignes en amont
de leur exposition par le pilote `gpiochip`.

**Diagnostic reproductible :**

```bash
grep -v '^#' /boot/firmware/config.txt | grep -v '^$'
gpioinfo | grep -i used
```

**Solution :** ligne commentée plutôt que supprimée, afin de conserver la trace de l'essai,
puis redémarrage.

**Leçon :** une modification de `config.txt` survit à tous les redémarrages et n'apparaît
dans aucun message d'erreur — l'erreur indique seulement qu'une broche est occupée, jamais
par quoi. Toute broche affectée à un overlay doit être notée au moment de l'ajout, et
l'overlay retiré dès la fin de l'essai. C'est le type de résidu de dépannage qui empoisonne
une session plusieurs semaines plus tard.

## F4 — Minimum local du champ de potentiel

Deux obstacles rapprochés, un de chaque côté, et la décision affichée était « tout droit » :

```
  10.5  77.3   4.6  |     19     20  |  tout droit
```

Un obstacle à 4,6 cm à droite, un autre à 10,5 cm à gauche, et le robot avance entre les
deux.

**Ce n'est pas un bruit de mesure ni une erreur de code.** Les deux distances sont sous
`D_MIN`, les deux répulsions valent donc exactement la même valeur plafond, et la force
latérale nette est nulle. Le champ de potentiel ne distingue pas « aucun obstacle » de
« bloqué symétriquement des deux côtés » : dans les deux cas la résultante est zéro.

C'est le **minimum local**, défaut connu et documenté des méthodes de champ de potentiel.
L'information manquante est absente de la résultante, donc aucun réglage de gain ne peut
le corriger.

**Solution :** un critère absolu, indépendant du calcul de forces.

```
Si une distance quelconque est inférieure à D_PANIQUE, arrêt,
quel que soit l'équilibre des forces.
```

`D_PANIQUE` fixé à 15 cm, valeur dérivée de la demi-largeur du châssis.

**Leçon :** une limite mathématique de la méthode choisie ne se corrige pas en ajustant ses
paramètres. Elle se corrige en ajoutant un critère extérieur à la méthode.

## F5 — Capteurs latéraux sans seuil d'arrêt

Un obstacle stable à 10,5 cm du flanc gauche laissait le robot avancer pendant 1,2 seconde
avec des consignes de 35 et 4.

Seul le capteur central possédait un seuil d'arrêt. Or un châssis à chenilles de 20 cm de
large ne peut pas pivoter avec un obstacle à 10 cm de son flanc : la chenille le percute
avant que le virage soit amorcé.

**Solution :** le seuil de panique de F4 s'applique aux trois capteurs, pas seulement au
central.

## F6 — Arrêt d'urgence relâché par une mesure aberrante isolée

Trente trames consécutives en arrêt, puis une trame unique relâchant les moteurs vers un
obstacle à 9,1 cm :

```
  17.0  20.5   9.1  |      5     34  |  vire a gauche
```

La décision était recalculée à chaque trame depuis la mesure brute, sans mémoire d'état.
Une seule lecture aberrante du capteur central — 20,5 cm au lieu des 16 réels — suffisait à
relâcher l'arrêt pendant 100 ms.

**Solution :** l'arrêt devient un état verrouillé, armé dès la première trame dangereuse et
relâché seulement après huit trames propres consécutives.

Une première version exigeait deux trames dangereuses pour armer, par prudence contre les
faux arrêts. C'était un mauvais arbitrage, visible sur les journaux :

```
   ---  77.7   4.2 |    -13     53  |  vire a gauche
   ---  77.7   4.2 |      0      0  |  ARRET - obstacle a 4 cm (droite)
```

Une consigne moteur envoyée pendant 100 ms avec un obstacle à 4,2 cm.

**Leçon :** l'hystérésis d'un état de sécurité doit être asymétrique. Les deux erreurs
n'ont pas le même coût : un faux arrêt coûte une fraction de seconde, un arrêt manqué coûte
le châssis. Entrée immédiate, sortie lente.

Une fenêtre de sortie de cinq trames s'est également révélée insuffisante : l'arrêt se
relâchait à 4/5 alors que l'obstacle était encore présent. Portée à huit après mesure.

## F7 — Diaphonie entre capteurs à ultrasons

Valeurs physiquement impossibles sur un même capteur en trois dixièmes de seconde :

```
   5.9   6.5  54.5
   6.5   6.5 ---
   6.8   6.5 ---
   6.8   6.8   4.2
```

Et ailleurs, dix trames consécutives identiques au dixième de centimètre près : `gpiozero`
renvoie sa dernière valeur en cache lorsqu'aucun écho ne revient.

**Cause :** les trois capteurs émettent presque simultanément dans leurs fils d'exécution
respectifs. À courte distance, l'impulsion d'un capteur atteint le récepteur d'un autre.

**Solution :** filtre médian sur une fenêtre de cinq échantillons par capteur.

La médiane plutôt que la moyenne : sur la séquence `5,2 → 54,5 → 4,2`, la médiane renvoie
une valeur plausible, tandis que la moyenne aurait renvoyé 21 cm, c'est-à-dire un obstacle
inexistant. Une moyenne intègre partiellement une aberration ; une médiane l'élimine
complètement.

## F8 — Paramètre devenu inatteignable par interaction avec un seuil de sécurité

```
   ---  76.9  15.2 |      0     39  |  vire a gauche
```

`D_MIN = 10 cm` plafonnait la force de répulsion, mais `D_PANIQUE = 15 cm` arrêtait le
robot avant. La plage 15–10 cm était donc inatteignable en mouvement : lorsque la fonction
de répulsion est appelée, toutes les distances valent au moins 15.

Conséquence : la correction maximale réellement atteignable valait

```
KP_OBS × (1/15 − 1/60) = KP_OBS × 0,0500
```

et non la valeur calculée à partir de `D_MIN`, supérieure de deux tiers. Le gain avait été
dimensionné sur une plage que le seuil de sécurité rendait inaccessible.

**Ce défaut ne produisait aucune anomalie de comportement.** Le robot réagissait
raisonnablement, simplement avec une correction maximale de 20 au lieu des 33 documentés.
L'écart entre comportement réel et comportement supposé était invisible sans le calcul
explicite de la borne.

**Solution :** `D_MIN` aligné sur `D_PANIQUE`, ce qui supprime le code mort, et gain
recalculé sur la plage réelle.

**Leçon :** deux paramètres corrects isolément peuvent être incompatibles. Chaque fois
qu'un seuil de sécurité est ajouté, les bornes des calculs existants doivent être
revérifiées : la sécurité peut rendre une partie du domaine de calcul inatteignable sans
qu'aucun test ne le signale.

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

**Une limite de la méthode ne se corrige pas en ajustant ses paramètres.** Le minimum local
du champ de potentiel ne venait pas d'un mauvais réglage mais de l'absence de l'information
dans la résultante. Sa correction a demandé un critère extérieur à la méthode.

**Un seuil de sécurité ajouté peut rendre une partie d'un calcul inatteignable.** Deux
paramètres corrects isolément se sont révélés incompatibles, sans qu'aucune anomalie de
comportement ne le signale. Après tout ajout d'un seuil, les bornes des calculs existants
doivent être revérifiées.

**L'hystérésis d'un état de sécurité doit être asymétrique.** Un faux arrêt coûte une
fraction de seconde, un arrêt manqué coûte le châssis. Entrée immédiate, sortie lente.

**Une modification de configuration système est un résidu durable.** Un overlay ajouté dans
`config.txt` lors d'un dépannage a bloqué une broche plusieurs semaines plus tard, sans
apparaître dans aucun message d'erreur. Toute broche réservée par un overlay doit être
notée à l'ajout et l'overlay retiré dès la fin de l'essai.
