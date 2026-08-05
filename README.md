# Robot Mobile Autonome — Pick & Place

**Auteure :** Saida Fatimatou Zahraa Diouf

---

## Description du projet

Robot mobile a chenilles capable de naviguer de facon autonome, de se localiser dans l'espace, de detecter un objet cible par vision, de le saisir avec un bras robotique, et de le transporter d'un point A a un point B defini.

Le systeme fonctionne en deux modes : teleopertion via manette Xbox, et navigation entierement autonome. Chaque phase de developpement ajoute une couche d'autonomie sur la precedente. Toutes les decisions de conception sont justifiees par des mesures empiriques plutot que par des hypotheses theoriques.

---

## Etat actuel

| Phase | Description | Statut |
|---|---|---|
| 1 | Assemblage hardware et controle moteur I2C | Termine |
| 2 | Teleoperation Xbox via ESP32 Bluetooth | Termine |
| 3 | Odometrie, calibration moteurs, asservissement de cap | En cours |
| 4 | Evitement d'obstacles (HC-SR04) | Planifie |
| 5 | Navigation autonome A vers B | Planifie |
| 6 | Vision — detection de balle (OpenCV) | Planifie |
| 7 | Bras robotique 5-DOF (STM32) | Planifie |
| 8 | Pick & place autonome | Objectif final |

---

## Architecture systeme

```
Manette Xbox (Bluetooth)
        |
      ESP32 TTGO T-Display     -- Pile BLE (NimBLE), traitement joystick,
        |  UART 115200 bauds      ecran TFT dashboard, boucle 50 Hz (FreeRTOS)
        |
   Raspberry Pi 4B              -- Odometrie, asservissement de cap, planification
        |  Bus I2C
        |
  Hiwonder Encoder Motor        -- Driver moteur boucle fermee, adresse 0x34
  Module V1.4
     /           \
Moteur M1       Moteur M2
(gauche)        (droite)

Gyroscope MPU6050               -- Mesure du cap, adresse 0x68
HC-SR04 ultrason                -- Detection d'obstacles (Phase 4+)

Alimentation :
LiPo 7.4V 2200mAh  ->  Hiwonder (moteurs)
Powerbank USB-C    ->  Raspberry Pi
ESP32              ->  USB (developpement) / buck LM2596 5V (autonomie complete)
```

---

## Hardware

| Composant | Role |
|---|---|
| Chassis Hiwonder a chenilles aluminium | Locomotion tout-terrain |
| Raspberry Pi 4B 4GB | Calcul central, Python, odometrie |
| ESP32 TTGO T-Display V1.1 (S3) | Bluetooth Xbox, pont UART, ecran TFT |
| STM32 | Controle bras robotique (Phase 7, reserve) |
| Hiwonder Encoder Motor Module V1.4 | Driver moteur + lecture encodeurs, I2C |
| MPU6050 IMU | Gyroscope pour asservissement de cap |
| HC-SR04 | Detection d'obstacles |
| LiPo Zeee 7.4V 2200mAh 50C | Alimentation moteurs |
| Manette Xbox Core Wireless | Entree teleopertion |

---

## Constantes de calibration (Phase 3, mesurees empiriquement)

| Constante | Valeur | Methode |
|---|---|---|
| METRES_PAR_PULSE | 1,05e-4 m/impulsion | Mesure au metro ruban sur 90 cm, 4 essais |
| ENTRAXE_EFF | 0,219 m | Methode rotation, 2 mesures independantes |
| K_RIGHT | 1,0 (neutralise) | Regulation interne suffisante en regime non sature |
| Plage de consigne utile | 10 a 30 | Saturation mesuree a partir de 40 |
| KP asservissement cap | 0,7 | Reglage empirique, 4 niveaux de gain testes |
| TURN_SPEED | 7 | Compensation inertie necessaire au-dela de cette valeur |
| ALPHA (fusion gyro) | 0,98 | Gyroscope dominant dans le filtre complementaire |

La valeur theorique de METRES_PAR_PULSE tiree des specifications moteur etait
de 2,36e-5 m/impulsion — facteur 3,8 d'ecart avec la valeur mesuree au sol.
Utiliser la valeur theorique aurait fausse toute l'odometrie. La mesure physique
est obligatoire.

---

## Performance mesuree (Phase 3)

| Methode | Deviation laterale sur 2 m |
|---|---|
| Encodeurs seuls, sans rampe | 11,5 cm |
| Encodeurs + rampe de demarrage | 5 a 7 cm |
| Asservissement de cap gyroscope (KP=0,7) | environ 1 cm |

Erreur de cap sur 3 m avec asservissement en boucle fermee :
inferieure a 2 degres, constante sur 4 essais.

---

## Structure du depot

```
mobile-manipulator-robot/
|
|-- README.md                        Ce fichier
|
|-- docs/
|   |-- hardware.md                  Tableaux de branchement, registres I2C, pins
|   |-- phase2_readme.md             Documentation Phase 2 : teleoperation Xbox
|   |-- phase3_part1_motor_balance.md   Caracterisation desequilibre moteur
|   |-- phase3_parts2_3_odometry.md     Conversion pulsions/metres, entraxe, integration pose
|   |-- phase3_part4_gyro_heading.md    Fusion inertielle, asservissement cap, rotation 90 deg
|   |-- data_collection_plan.md      Protocoles experimentaux pour les 8 phases
|
|-- firmware/
|   |-- esp32/
|       |-- platformio.ini           Configuration build, versions librairies
|       |-- src/
|           |-- main.cpp             Firmware ESP32 complet (Xbox BLE + UART + TFT)
|
|-- scripts/
|   |-- phase1/
|   |   |-- test_motors.py           Test I2C moteurs de base (avance, recule, tourne)
|   |
|   |-- phase2/
|   |   |-- xbox_receiver.py         Reception UART + pont I2C Hiwonder (teleoperation)
|   |
|   |-- phase3/
|       |-- motor_balance.py         Caracterisation desequilibre moteur (18 essais)
|       |-- odom_fusion.py           Filtre complementaire gyroscope + encodeurs
|       |-- heading_control.py       PID asservissement ligne droite
|       |-- turn_90.py               Rotation 90 degres assistee par gyroscope
|
|-- data/
|   |-- phase3/
|       |-- (tableaux resultats bruts)
|
|-- media/
    |-- photos/                      Photos de construction par phase
```

---

## Lancer le robot

Connexion SSH (hotspot mobile requis, meme reseau que le RPi) :
```bash
ssh indigozafa@indigowing.local
```

Teleopertion (Phase 2) :
```bash
python3 ~/scripts/phase2/xbox_receiver.py
```

Asservissement de cap en ligne droite (Phase 3) :
```bash
python3 ~/scripts/phase3/heading_control.py
```

Le robot se deplace uniquement tant que le script actif tourne.
Fermer la session SSH ou arreter le script (Ctrl+C) arrete les moteurs.

---

## Environnement de developpement

| Outil | Usage |
|---|---|
| VS Code + PlatformIO | Firmware C++ ESP32 |
| Python 3 (Raspberry Pi) | Controle moteur, odometrie, fusion capteurs |
| smbus2 | Communication I2C (Python) |
| NimBLE-Arduino 2.3.6 | Pile BLE pour manette Xbox |
| XboxSeriesXControllerESP32_asukiaaa 1.1.1 | Lecture manette Xbox |
| TFT_eSPI 2.5.43 | Ecran TFT (ST7789V, parallele 8 bits) |

---

## Contact

Portfolio : fatima02d.github.io
GitHub : github.com/fatima02d
LinkedIn : linkedin.com/in/saida-fatimatou-zahraa-diouf
