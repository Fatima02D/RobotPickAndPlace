# Robot Mobile Autonome — Pick & Place

**Auteure :** Saida Fatimatou Zahraa Diouf

**Dépôt :** github.com/fatima02d/RobotPickAndPlace

---

## Description

Robot mobile à chenilles conçu pour naviguer de façon autonome, se localiser dans
l'espace, détecter un objet cible par vision, le saisir avec un bras robotique, et le
transporter d'un point A vers un point B défini.

Le système fonctionne en deux modes complémentaires : téléopération via manette Xbox et
navigation entièrement autonome. Chaque phase de développement ajoute une couche
d'autonomie sur la précédente. Toutes les constantes physiques du système ont été
mesurées empiriquement plutôt que reprises de spécifications théoriques.

---

## État d'avancement

| Phase | Description | Statut |
|---|---|---|
| 1 | Assemblage hardware et contrôle moteur I2C | Terminé |
| 2 | Téléopération Xbox via ESP32 Bluetooth | Terminé |
| 3 | Odométrie, calibration, asservissement de cap | Terminé |
| 4 | Évitement d'obstacles (3x HC-SR04) | Terminé |
| 5 | Navigation autonome vers coordonnées cibles | En cours |
| 6 | Vision — détection de balle (OpenCV) | Planifié |
| 7 | Bras robotique 5-DOF (STM32) | Planifié |
| 8 | Pick & place autonome complet | Objectif final |

---

## Architecture système

```
Manette Xbox (Bluetooth BLE)
        |                          Boutons A / B / Y : sélection du mode
      ESP32 TTGO T-Display S3    -- Pile NimBLE, traitement joystick,
        |  UART 115200 bauds        écran TFT, boucle 50 Hz FreeRTOS
        |  Trame : M,L,R
        |
   Raspberry Pi 4B                -- Odométrie, évitement, asservissement
        |  Bus I2C
        |
  Hiwonder Encoder Motor          -- Driver moteur boucle fermée, adresse 0x34
  Module V1.4
     /           \
Moteur M1       Moteur M2
(gauche)        (droite)

MPU6050                            -- Gyroscope, mesure du cap, adresse 0x68
HC-SR04 (x3)                       -- Détection d'obstacles gauche/centre/droite

Alimentation :
LiPo 7,4V 2200mAh  ->  Hiwonder PWR (logique + moteurs), en direct
Powerbank USB-C    ->  Raspberry Pi
LiPo -> LM2596 5V  ->  ESP32
```

La broche 5 V du port I2C de la Hiwonder n'est raccordée à rien. Sur la première carte,
elle délivrait 7 V — tension brute de la batterie — et a détruit le contrôleur I2C ainsi
que le premier Raspberry Pi. Voir `docs/troubleshooting.md`, F1.

### Modes de fonctionnement

Le mode se choisit à la manette et s'affiche sur l'écran de l'ESP32.

| Bouton | Mode | Qui commande les moteurs |
|---|---|---|
| A | Téléopération | Le joystick, relayé tel quel |
| B | Autonome | La logique d'évitement, sur le Raspberry Pi |
| Y | Arrêt | Personne, consignes nulles |

Le mode au démarrage est l'arrêt. Toute déconnexion de la manette, ou tout silence de la
liaison UART dépassant 300 ms, y ramène.

---

## Matériel

| Composant | Rôle |
|---|---|
| Châssis Hiwonder à chenilles aluminium | Locomotion tout-terrain |
| Raspberry Pi 4B 4GB | Calcul central, Python, odométrie |
| ESP32 TTGO T-Display V1.1 (S3) | Bluetooth Xbox, pont UART, écran TFT |
| STM32 | Contrôle bras robotique (Phase 7, réservé) |
| Hiwonder Encoder Motor Module V1.4 | Driver moteur et lecture encodeurs, I2C |
| MPU6050 (GY-521) | Gyroscope pour asservissement de cap |
| HC-SR04 (x3) | Détection d'obstacles |
| LiPo Zeee 7,4V 2200mAh 50C | Alimentation moteurs |
| Powerbank Podoru 5000mAh | Alimentation Raspberry Pi |
| Manette Xbox Core Wireless | Entrée téléopération |

---

## Constantes calibrées (Phase 3)

Toutes ces valeurs ont été mesurées sur ce robot spécifique.

| Constante | Valeur | Méthode de mesure |
|---|---|---|
| METRES_PAR_PULSE | 1,05e-4 m/impulsion | Mètre ruban sur 90 cm, 4 essais |
| ENTRAXE_EFF | 0,219 m | Méthode rotation, 2 mesures indépendantes |
| K_RIGHT | 1,0 (neutralisé) | Régulation interne suffisante en régime non saturé |
| Plage de consigne utile | 10 à 30 | Saturation mesurée à partir de 40 |
| KP asservissement cap | 0,7 | Réglage empirique, 4 gains testés |
| TURN_SPEED | 7 | Compensation de l'inertie |
| TURN_CUTOFF | 80 deg | Coupure moteurs, l'inertie termine à 90 deg |
| ALPHA fusion gyro | 0,98 | Gyroscope dominant dans le filtre complémentaire |

La valeur théorique de METRES_PAR_PULSE issue des spécifications moteur était de
2,36e-5 m/impulsion, soit un facteur 3,8 d'écart avec la mesure au sol. Utiliser la
valeur théorique aurait faussé l'intégralité de l'odométrie.

## Constantes calibrées (Phase 4)

| Constante | Valeur | Origine |
|---|---|---|
| D_INFLUENCE | 60 cm | Portée au-delà de laquelle un obstacle est ignoré |
| D_PANIQUE | 15 cm | Dérivée de la demi-largeur du châssis |
| D_MIN | 15 cm | Aligné sur D_PANIQUE |
| D_ARRET | 20 cm | Seuil d'arrêt du capteur central |
| KP_OBS | 600 | Réglage empirique, 3 itérations |
| POIDS_CENTRE | 2,0 | Un obstacle de face est sur la trajectoire |
| Hystérésis d'arrêt | 1 trame en entrée, 8 en sortie | Asymétrie délibérée |
| Fenêtre du filtre médian | 5 échantillons | Contre la diaphonie entre capteurs |
| Recul de dégagement | vitesse 15, 0,8 s | Court car aucun capteur arrière |
| Pivot de dégagement | vitesse 35, 0,7 s | Vers le côté le plus dégagé |

Profil de correction mesuré, obstacle approché progressivement :

| Distance | Consignes G / D |
|---|---|
| 43 cm | 23 / 16 |
| 39 cm | 25 / 14 |
| 35 cm | 27 / 12 |
| 17 cm | 46 / -6 |

---

## Performance mesurée

**Déviation en ligne droite sur 2 m :**

| Méthode | Déviation |
|---|---|
| Encodeurs seuls, sans rampe | 11,5 cm |
| Encodeurs avec rampe de démarrage | 5 à 7 cm |
| Asservissement gyroscope KP=0,7 | environ 1 cm |

**Parcours en carré (4 côtés de 1 m, 5 essais) :**

| Métrique | Résultat |
|---|---|
| Distance par côté | 100,0 à 101,2 cm |
| Cap final après 4 rotations | 268,4 deg en moyenne (cible 270) |
| Erreur de cap moyenne | environ 2 deg |
| Erreur de bouclage (3 essais) | 12, 16, 12 cm — moyenne 13,3 cm |
| Erreur cumulée sur 4 m | 3,3 % |

---

## Structure du dépôt

```
RobotPickAndPlace/
|
|-- README.md                          Ce fichier
|
|-- docs/
|   |-- hardware.md                    Branchements, registres I2C, pins
|   |-- logbook.md                     Journal de bord de chaque session
|   |-- troubleshooting.md             Problèmes rencontrés et solutions
|   |-- phase2_readme.md               Documentation Phase 2
|   |-- phase3_odometrie.md            Documentation Phase 3
|   |-- phase4_evitement.md            Documentation Phase 4
|   |-- plan_collecte_donnees.md       Protocoles expérimentaux des 8 phases
|
|-- firmware/
|   |-- esp32/
|       |-- platformio.ini             Configuration build et librairies
|       |-- src/
|           |-- main.cpp               Firmware ESP32 complet
|
|-- scripts/
|   |-- phase1/
|   |   |-- test_motors.py             Test moteurs I2C de base
|   |
|   |-- phase2/
|   |   |-- xbox_receiver.py           Réception UART et pont I2C
|   |
|   |-- phase3/
|   |   |-- motor_balance.py           Caractérisation du déséquilibre moteur
|   |   |-- heading_control.py         Asservissement de cap en ligne droite
|   |   |-- turn_90.py                 Rotation 90 deg assistée gyroscope
|   |   |-- square_path.py             Parcours en carré automatique
|   |
|   |-- phase4/
|       |-- test_hcsr04_triple.py      Validation des 3 capteurs ultrason
|       |-- evitement.py               Module : constantes, filtrage, décision
|       |-- obstacle_logic_test.py     Réglage en simulation, sans moteurs
|       |-- mode_receiver.py           Sélecteur de mode, programme principal
|
|-- data/                              Données brutes des expériences
|
|-- images/                            Photos de construction par phase
```

---

## Lancer le robot

**Téléverser le firmware ESP32** (dans PowerShell Windows, pas Ubuntu) :
```powershell
cd C:\Users\HP\OneDrive\Documents\PlatformIO\Projects\esp32_xbox_controller
C:\Users\HP\.platformio\penv\Scripts\platformio.exe run --target upload --upload-port COM8
```

Le chemin complet est nécessaire : `pio` n'est pas dans le PATH du système. Le port doit
être précisé explicitement, sinon l'extension VS Code impose un port Bluetooth mémorisé
dans ses réglages utilisateur.

**Se connecter au Raspberry Pi :**
```bash
ssh indigozafa@indigowing.local
```

**Programme principal — sélecteur de mode :**
```bash
python3 ~/mode_receiver.py
```

C'est le seul programme à lancer en usage normal. Il lit le mode choisi à la manette et
oriente la commande des moteurs en conséquence. `evitement.py` doit se trouver dans le
même dossier : c'est un module, importé par ce programme, jamais exécuté seul.

**Réglage de l'évitement, sans moteurs :**
```bash
python3 ~/obstacle_logic_test.py
```

Affiche les consignes qui seraient envoyées, sans rien actionner. C'est là qu'on ajuste
les constantes de `evitement.py` en sécurité.

**Téléopération seule (Phase 2, conservé pour référence) :**
```bash
python3 ~/xbox_receiver.py
```

Ce script attend l'ancien format de trame à deux champs. Il n'est plus compatible avec le
firmware actuel.

**Asservissement de cap :**
```bash
python3 ~/heading_control.py
```

**Parcours en carré :**
```bash
python3 ~/square_path.py
```

Le robot se déplace uniquement tant que le script actif tourne. Fermer la session SSH ou
interrompre le script avec Ctrl+C arrête les moteurs.

---

## Commandes de maintenance

À exécuter après chaque reflash de la carte micro SD :

```bash
# Effacer l'ancienne clé SSH
ssh-keygen -R indigowing.local

# Réactiver I2C
sudo raspi-config     # Interface Options -> I2C -> Yes

# Réactiver le port série
sudo raspi-config     # Interface Options -> Serial Port
                      # Login shell : No / Hardware : Yes

sudo reboot
```

Vérification après redémarrage :
```bash
i2cdetect -y 1        # doit afficher 0x34 et 0x68
ls /dev/ttyS0         # doit exister
```

---

## Environnement de développement

| Outil | Usage |
|---|---|
| VS Code et PlatformIO | Firmware C++ ESP32 |
| Python 3 (Raspberry Pi) | Contrôle moteur, odométrie, capteurs |
| smbus2 | Communication I2C |
| pyserial | Communication UART |
| RPi.GPIO | Lecture capteurs ultrason |
| NimBLE-Arduino 2.3.6 | Pile BLE pour manette Xbox |
| XboxSeriesXControllerESP32_asukiaaa 1.1.1 | Lecture manette Xbox |
| TFT_eSPI 2.5.43 | Écran TFT (ST7789V, parallèle 8 bits) |

---

## Contact

Portfolio : fatima02d.github.io
GitHub : github.com/fatima02d
LinkedIn : linkedin.com/in/saida-fatimatou-zahraa-diouf
