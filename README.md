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
d'autonomie sur la précédente. 

---

## État d'avancement

| Phase | Description | Statut |
|---|---|---|
| 1 | Assemblage hardware et contrôle moteur I2C | Terminé |
| 2 | Téléopération Xbox via ESP32 Bluetooth | Terminé |
| 3 | Odométrie, calibration, asservissement de cap | Terminé |
| 4 | Évitement d'obstacles (3x HC-SR04) | En cours |
| 5 | Navigation autonome vers coordonnées cibles | Planifié |
| 6 | Vision — détection de balle (OpenCV) | Planifié |
| 7 | Bras robotique 5-DOF (STM32) | Planifié |
| 8 | Pick & place autonome complet | Objectif final |

---

## Architecture système

```
Manette Xbox (Bluetooth BLE)
        |
      ESP32 TTGO T-Display S3    -- Pile NimBLE, traitement joystick,
        |  UART 115200 bauds        écran TFT, boucle 50 Hz FreeRTOS
        |
   Raspberry Pi 4B                -- Odométrie, asservissement, planification
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
LiPo 7,4V 2200mAh  ->  Hiwonder PWR (moteurs)
Powerbank USB-C    ->  Raspberry Pi
ESP32              ->  USB (développement)
```

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
|   |-- phase3_part1_calibration_moteurs.md
|   |-- phase3_parts2_3_odometrie.md
|   |-- phase3_part4_fusion_gyro.md
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
C:\Users\HP\.platformio\penv\Scripts\platformio.exe run --target upload
```

**Se connecter au Raspberry Pi :**
```bash
ssh indigozafa@indigowing.local
```

**Téléopération :**
```bash
python3 ~/xbox_receiver.py
```

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
