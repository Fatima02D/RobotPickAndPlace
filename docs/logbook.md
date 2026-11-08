# Journal de Bord — Robot Mobile Autonome

**Projet :** Robot Mobile Autonome Pick & Place
**Auteure :** Saida Fatimatou Zahraa Diouf
**Dépôt :** github.com/fatima02d/RobotPickAndPlace

---

## Format

```
## AAAA-MM-JJ

**Objectif :**
**Accompli :**
**Problèmes rencontrés :**
**Solutions :**
**Prochaine étape :**
```

---

## 2026-04-27 — Base matérielle

**Objectif :** Établir la base matérielle complète du robot

**Accompli :**
- Châssis Hiwonder assemblé, moteurs connectés sur M1 et M2
- RPi 4B vers Hiwonder : SDA, SCL, 5V, GND branchés (I2C)
- HC-SR04 branché avec diviseur de tension 1k/2k sur ECHO
- ESP32 TTGO T-Display identifié et pins de communication définies
- LiPo Zeee 7,4V 2200mAh 50C retenue pour l'alimentation des moteurs
- Architecture système complète définie

**Problèmes rencontrés :**
- Carte SD standard incompatible avec le RPi 4B qui exige une micro SD
- Connecteur XT30 de la LiPo incompatible avec le port PWR Hiwonder (JST)
- Chargeur LiPo manquant

**Solutions :**
- Chargeur CHICIRIS TE3AC commandé, incluant un adaptateur Deans vers JST
- Micro SD SanDisk 32GB ajoutée à la liste d'achats

**Prochaine étape :** Installer Raspberry Pi OS, tester la communication I2C

---

## 2026-04-28 — Phase 1 complète

**Objectif :** Installer l'OS sur le RPi et piloter les moteurs

**Accompli :**
- Micro SD flashée avec Raspberry Pi OS 64-bit, SSH activé au flash
- Nom d'hôte IndigoWing, utilisateur indigozafa
- Connexion SSH établie via partage de connexion mobile
- I2C activé, Hiwonder détectée à l'adresse 0x34
- Script Python de test moteurs écrit et exécuté
- Robot avance, recule et tourne — Phase 1 terminée

**Problèmes rencontrés :**
- SSH non fonctionnel au premier flash : la case n'était pas cochée dans l'Imager
- Nom d'hôte non résolvable : ordinateur et RPi sur des réseaux différents
- Avertissement de changement de clé SSH après reflash
- Court-circuit du RPi quand la Powerbank et le 5V Hiwonder étaient branchés ensemble
- Registres I2C incorrects (0x01) : les moteurs ne réagissaient pas
- Fils moteurs M1/M2 débranchés : bruit moteur sans mouvement

**Solutions :**
- Reflasher en vérifiant visuellement l'activation SSH
- Utiliser le partage de connexion mobile comme réseau commun
- `ssh-keygen -R indigowing.local` pour effacer l'ancienne clé
- Une seule source d'alimentation par composant
- Registres corrects : MOTOR_TYPE=20, POLARITY=21, SPEED=51
- Reconnecter fermement les connecteurs JST des moteurs

**Prochaine étape :** Phase 2, téléopération Xbox via ESP32

---

## 2026-06-15 — Connexion de la manette Xbox

**Objectif :** Programmer l'ESP32 pour recevoir la manette et relayer au RPi

**Accompli :**
- Projet PlatformIO créé, carte lilygo-t-display-s3
- Versions de librairies compatibles identifiées via un ancien projet académique
- Code ESP32 écrit avec FreeRTOS, tâche Xbox à 50 Hz
- Manette Xbox connectée en Bluetooth, valeurs joystick lues correctement

**Problèmes rencontrés :**
- ESP32-BLE-Gamepad incompatible avec NimBLE, retirée
- Bluepad32 non installable via lib_deps PlatformIO, abandonnée
- XboxSeriesXControllerESP32 incompatible avec NimBLE 1.4.x et 2.5.x
- Carte mal sélectionnée : lilygo-t-display au lieu de lilygo-t-display-s3

**Solutions :**
- NimBLE 2.3.6 retenue, version validée dans un projet antérieur
- Carte corrigée dans platformio.ini

**Prochaine étape :** Écrire le script Python de réception UART sur le RPi

---

## 2026-06-20 — Chaîne complète Xbox vers moteurs

**Objectif :** Faire fonctionner le flux Xbox vers ESP32 vers RPi vers moteurs

**Accompli :**
- Test loopback confirmant le bon fonctionnement du port série du RPi
- Liaison UART validée avec un code ESP32 minimal
- Script xbox_receiver.py écrit et fonctionnel
- Les quatre directions répondent correctement à la manette

**Problèmes rencontrés :**
- GPIO43/44 testés comme alternative : ce sont les pins UART0 natifs, aucune donnée ne
  passait
- GND non connecté entre ESP32 et RPi : données corrompues, erreurs de décodage UTF-8
- Joystick non centré au repos : mouvement involontaire constant
- Code de test fixe laissé par erreur sur l'ESP32 : faux diagnostic de bug

**Solutions :**
- Retour aux pins GPIO17 (TX) et GPIO2 (RX)
- Masse commune rétablie entre ESP32 et RPi
- Zone morte augmentée à 2000 sur la plage brute du joystick

**Prochaine étape :** Valider les quatre directions en conditions réelles

---

## 2026-06-27 — Correction de direction et affichage TFT

**Objectif :** Corriger le bug de direction restant et ajouter l'affichage

**Accompli :**
- Cause réelle du bug identifiée : dépassement de capacité sur int16_t
- Calculs passés en int32_t avec calibration automatique du centre au démarrage
- Les quatre directions répondent correctement, sans mouvement involontaire
- Affichage TFT ajouté : titre, date et heure NTP, état manette, batterie, consignes
  moteur

**Problèmes rencontrés :**
- Erreur de compilation avr/eeprom.h : librairie AVR incluse automatiquement
- Tentative d'alimenter l'ESP32 par la sortie 5V Hiwonder : 2,7V mesurés à vide

**Solutions :**
- `lib_ldf_mode = chain+` dans platformio.ini, puis nettoyage du projet
- ESP32 maintenu sur alimentation USB en attendant un convertisseur dédié

**Prochaine étape :** Phase 3, odométrie

---

## 2026-07 — Phase 3, odométrie et asservissement

**Objectif :** Doter le robot d'une estimation de sa propre position

**Accompli :**
- Caractérisation du déséquilibre moteur sur 18 essais, 6 points de fonctionnement
- Relation impulsions vers mètres établie par mesure au sol
- Entraxe effectif déterminé expérimentalement par la méthode de rotation
- Fusion gyroscope-encodeurs implémentée avec filtre complémentaire
- Asservissement de cap en ligne droite validé
- Rotation de 90 degrés assistée par gyroscope réglée
- Parcours en carré validé sur 5 essais

**Résultats mesurés :**

Déviation en ligne droite sur 2 m :

| Méthode | Déviation |
|---|---|
| Encodeurs seuls, sans rampe | 11,5 cm |
| Encodeurs avec rampe | 5 à 7 cm |
| Asservissement gyroscope KP=0,7 | environ 1 cm |

Parcours en carré, 4 côtés de 1 m, 5 essais :

| Métrique | Résultat |
|---|---|
| Distance par côté | 100,0 à 101,2 cm |
| Cap final (cible 270 deg) | 268,4 deg en moyenne |
| Erreur de cap moyenne | environ 2 deg |
| Erreur de bouclage, 3 essais | 12, 16, 12 cm |
| Erreur cumulée sur 4 m | 3,3 % |

**Problèmes rencontrés :**
- Rotation infinie : le gyroscope retourne des valeurs négatives en rotation gauche, la
  condition d'arrêt ne se déclenchait jamais
- Robot qui tournait en avançant pendant le parcours en carré
- Valeur théorique METRES_PAR_PULSE fausse d'un facteur 3,8
- Déséquilibre moteur mesuré en partie 1 révélé comme artefact de saturation

**Solutions :**
- Valeur absolue dans la condition d'arrêt de rotation
- La fonction d'avance corrige le cap à chaque cycle, pas seulement au démarrage
- Valeur mesurée au sol substituée à la valeur théorique
- K_RIGHT neutralisé à 1,0, la régulation interne suffit en régime non saturé

**Prochaine étape :** Phase 4, évitement d'obstacles

---

## 2026-08 — Phase 4, capteurs ultrason

**Objectif :** Valider les trois capteurs HC-SR04 et préparer l'évitement

**Accompli :**
- Trois capteurs HC-SR04 branchés et validés
- Lecture simultanée des trois distances confirmée
- Branchements définitifs établis sans conflit avec UART, SPI ou I2C

**Branchements retenus :**

| Capteur | TRIG | ECHO |
|---|---|---|
| Gauche | GPIO23 (Pin 16) | GPIO24 (Pin 18) |
| Centre | GPIO17 (Pin 11) | GPIO27 (Pin 13) |
| Droite | GPIO22 (Pin 15) | GPIO26 (Pin 37) |

**Problèmes rencontrés :**
- Surtension initiale : fils chauffants, un capteur détruit par court-circuit interne
- Confusion entre potentiomètre et convertisseur abaisseur
- Mini breadboards à l'origine de courts-circuits intermittents
- GPIO10 initialement choisi pour un ECHO : conflit avec SPI_MOSI
- Saturation des colonnes de la breadboard pour les connexions de masse

**Solutions :**
- LM2596 identifié correctement et réglé à 5V au multimètre avant connexion
- Test d'isolation capteur par capteur pour identifier celui qui était détruit
- Mini breadboards retirées, rails horizontaux de la breadboard principale utilisés
- ECHO droit déplacé sur GPIO26
- Capteurs alimentés directement par le RPi (45 mA au total, sans risque)

**Prochaine étape :** Intégrer la lecture des capteurs dans la boucle de contrôle,
ajouter le basculement entre mode téléopéré et mode autonome par bouton de manette

---

## 26 octobre 2026 — Diagnostic du contrôleur moteur et logique d'évitement

**Objectif :** Comprendre la disparition de l'adresse I2C `0x34`, puis avancer la Phase 4
sans le contrôleur moteur.

**Accompli :**
- Contrôleur Hiwonder diagnostiqué hors d'usage : la broche 5 V de son port I2C délivrait
  7 V, tension brute de la batterie, son régulateur interne étant court-circuité
  entrée-sortie. Explique rétrospectivement la destruction du premier Raspberry Pi.
- Architecture d'alimentation revue et règles permanentes établies.
- MPU6050 rétabli à `0x68` en ramenant son VCC sur la broche 1 du Raspberry Pi.
- Scripts de capteurs réécrits avec `gpiozero`, la bibliothèque native de Bookworm.
- Logique d'évitement développée et réglée en trois itérations, entièrement en simulation.

**Problèmes rencontrés :**
- `GPIO not allocated` puis `GPIO busy` sur GPIO24, survivant au redémarrage
- Minimum local du champ de potentiel : deux obstacles symétriques donnent une résultante
  nulle, interprétée comme voie libre
- Arrêt d'urgence relâché par une seule mesure aberrante
- Gain structurellement plafonné par une borne inatteignable

**Solutions :**
- Overlay `i2c-gpio` résiduel dans `config.txt` identifié : il réservait GPIO23 et GPIO24
  au démarrage, les deux broches du capteur gauche
- Seuil de panique absolu à 15 cm sur n'importe quel capteur
- Verrou d'arrêt asymétrique : 1 trame en entrée, 8 en sortie
- `D_MIN` aligné sur `D_PANIQUE`, gain recalculé à 600

**Prochaine étape :** Intégrer aux moteurs à la réception du contrôleur de remplacement

---

## 6 novembre 2026 — Réception du nouveau contrôleur

**Objectif :** Mettre en service le contrôleur moteur de remplacement sans répéter
l'incident précédent.

**Accompli :**
- Protocole de première mise sous tension appliqué : LiPo seule sur le port PWR, mesure
  de la broche 5 V du port I2C avant tout raccordement. Carte saine.
- Raccordement en trois fils seulement — SDA, SCL, GND — la broche 5 V restant libre.
- `0x34` et `0x68` détectés sur le bus.
- Moteurs validés avec `test_motors.py`.
- `hardware.md` corrigé : il indiquait encore un raccordement de la broche 5 V du port
  I2C au Pin 4 du Raspberry Pi, c'est-à-dire exactement le câblage qui avait détruit la
  première carte.

**Prochaine étape :** Tester le sélecteur de mode

---

## 7 novembre 2026 — Sélecteur de mode et manœuvre de dégagement

**Objectif :** Réunir téléopération et évitement autonome en un seul système commandé
depuis la manette.

**Accompli :**
- Sélecteur de mode opérationnel de bout en bout : manette, BLE, ESP32, UART, Raspberry
  Pi, I2C, moteurs. Boutons A, B et Y, mode affiché en bandeau coloré sur l'écran TFT.
- Deux sécurités indépendantes validées : repli en arrêt à la déconnexion de la manette,
  et repli sur silence UART de plus de 300 ms.
- Manœuvre de dégagement ajoutée — recul puis pivot vers le côté le plus dégagé — ce qui
  transforme l'arrêt devant un obstacle en véritable évitement.
- Capteur central pondéré par deux : un obstacle de face est sur la trajectoire.
- Phase 4 close.

**Problèmes rencontrés :**
- Redémarrage en boucle de l'ESP32 : `RPI_RX` sur GPIO27, broche réservée à la flash sur
  ESP32-S3
- Aucune sortie série sur USB, faute de `ARDUINO_USB_CDC_ON_BOOT`
- Téléversement dirigé vers COM6, un port Bluetooth, par un réglage utilisateur de VS Code
- Hôte d'extensions de VS Code planté en boucle
- Moteurs inertes depuis le dispatcher alors que `test_motors.py` fonctionnait
- Rotation lente au repos en téléopération
- Script dupliqué par un collage dans `nano` sur un fichier non vidé

**Solutions :**
- `RPI_RX` ramené sur GPIO2 ; les strapping pins du S3 sont GPIO0, GPIO3, GPIO45, GPIO46,
  pas GPIO2
- `-DARDUINO_USB_CDC_ON_BOOT=1` ajouté à `platformio.ini`
- Port précisé explicitement en ligne de commande, ce qui contourne le réglage mémorisé
- Consigne moteur réécrite toutes les 50 ms et masque `& 0xFF` appliqué
- Zone morte du joystick portée à 9000, et recalibration déclenchée par le bouton Y
- Vider le fichier avec `>` avant d'ouvrir `nano`, puis vérifier la taille avec `wc -c`

**Correctif retiré :** une reconfiguration périodique de la Hiwonder toutes les deux
secondes, destinée à rattraper les micro-coupures de la LiPo, dégradait le comportement
dans les deux modes. Réécrire `MOTOR_TYPE` pendant que les moteurs tournent demande au
contrôleur de reconfigurer son étage de puissance en pleine marche.

**Prochaine étape :** Phase 5, navigation autonome vers coordonnées cibles

---

## Éléments en suspens

**Connecteur de la LiPo.** Le connecteur Deans vers JST s'est débranché en cours
d'essai le 7 novembre, faisant perdre à la Hiwonder ses registres de configuration. Une
alimentation intermittente finira par causer un autre problème, ailleurs, plus difficile
à diagnostiquer. Aucun correctif logiciel ne la rattrape : la tentative de
reconfiguration périodique a aggravé la situation.

**Oscillation le long d'une paroi.** Le champ de potentiel n'a aucune mémoire de cap : il
pivote jusqu'à ce que le capteur se dégage, repart, se rapproche, recommence. Traité en
Phase 5, où l'existence d'un cap visé transforme l'évitement en déviation autour d'un
objectif.

**Alimentation autonome de l'ESP32.** Résolu. L'ESP32 est alimenté par un convertisseur
LM2596 réglé à 5,0 V depuis la LiPo, sa sortie négative rejoignant le rail de masse
commune. La sortie 5V du module Hiwonder, mesurée à 2,7 V à vide, n'a jamais été
utilisable.
