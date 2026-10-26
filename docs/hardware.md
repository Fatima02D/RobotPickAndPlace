# Référence Matériel et Branchements

**Projet :** Robot Mobile Autonome Pick & Place
**Auteure :** Saida Fatimatou Zahraa Diouf

---

## Bus I2C — appareils

| Appareil | Adresse | Rôle |
|---|---|---|
| Hiwonder Encoder Motor Module V1.4 | 0x34 | Commandes moteur, lecture encodeurs |
| MPU6050 (GY-521) | 0x68 | Gyroscope, mesure du cap |

## Registres Hiwonder

| Nom | Adresse | Description |
|---|---|---|
| MOTOR_TYPE_ADDR | 20 | Type de moteur (valeur 3 pour moteurs JGB) |
| MOTOR_ENCODER_POLARITY_ADDR | 21 | Polarité des encodeurs (valeur 0) |
| MOTOR_FIXED_SPEED_ADDR | 51 | Consigne de vitesse, 4 octets [M1,M2,M3,M4], plage -100 à 100 |
| MOTOR_ENCODER_TOTAL_ADDR | 60 | Compteurs cumulés, 4x int32 little-endian (16 octets) |

## Registres MPU6050

| Nom | Adresse | Description |
|---|---|---|
| PWR_MGMT_1 | 0x6B | Réveil du capteur (écrire 0x00) |
| GYRO_CONFIG | 0x1B | Plage du gyroscope (0x00 = 250 deg/s) |
| GYRO_ZOUT_H | 0x47 | Lecture de l'axe Z, 2 octets signés |

Facteur de conversion : 131,0 LSB par degré par seconde à FS_SEL=0.

---

## Branchements Raspberry Pi

### RPi vers Hiwonder (I2C)

| Pin physique RPi | Fonction | Pin Hiwonder |
|---|---|---|
| Pin 3 | SDA (GPIO2) | SDA |
| Pin 5 | SCL (GPIO3) | SCL |
| Pin 4 | 5V | 5V |
| Pin 6 | GND | GND |

### RPi vers MPU6050 (I2C, même bus)

| Pin physique RPi | Fonction | Pin MPU6050 |
|---|---|---|
| Pin 3 | SDA | SDA |
| Pin 5 | SCL | SCL |
| Pin 1 | 3,3V | VCC |
| Pin 9 | GND | GND |

Les deux appareils partagent le même bus I2C. Leurs adresses distinctes (0x34 et 0x68)
permettent au Raspberry Pi de les distinguer sans conflit.

### RPi vers ESP32 (UART)

| Pin physique RPi | Fonction | Pin ESP32 |
|---|---|---|
| Pin 8 | TX (GPIO14) | GPIO27 (RX) |
| Pin 10 | RX (GPIO15) | GPIO17 (TX) |
| Pin 14 | GND | GND |

Logique 3,3V des deux côtés, aucun adaptateur de niveau requis.

GPIO27 est utilisé pour la réception de l'ESP32 plutôt que GPIO2. GPIO2 est une broche
de configuration (strapping pin) : si la ligne TX du Raspberry Pi est maintenue haute au
moment du démarrage de l'ESP32, ce dernier peut ne pas démarrer correctement.

### RPi vers HC-SR04 (x3)

| Capteur | TRIG | ECHO |
|---|---|---|
| Gauche | GPIO23 (Pin 16) | GPIO24 (Pin 18) |
| Centre | GPIO17 (Pin 11) | GPIO27 (Pin 13) |
| Droite | GPIO22 (Pin 15) | GPIO26 (Pin 37) |

Alimentation des trois capteurs :
```
VCC (x3) -> RPi Pin 2 (5V)
GND (x3) -> RPi Pin 9 ou Pin 14 (GND)
```

Tous les pins GND du Raspberry Pi sont reliés en interne (Pin 6, 9, 14, 20, 25, 30, 34,
39). N'importe lequel convient.

Consommation totale des trois capteurs : environ 45 mA, très en dessous de la capacité
du rail 5V du Raspberry Pi.

### Diviseur de tension sur chaque ECHO

Le HC-SR04 émet un signal 5V sur sa broche ECHO. Les GPIO du Raspberry Pi acceptent
3,3V au maximum. Un diviseur résistif est obligatoire sur chaque ligne ECHO.

```
HC-SR04 ECHO (5V) ---- 1 kOhm ---- GPIO du RPi
                            |
                         2 kOhm
                            |
                        GND commun

Tension résultante = 5V x (2k / 3k) = 3,33V
```

La borne basse de chaque résistance 2 kOhm doit rejoindre le même rail GND que tous les
autres composants du montage.

### Moteurs vers Hiwonder

| Moteur | Connecteur | Port |
|---|---|---|
| Gauche | JST 6 fils | M1 |
| Droit | JST 6 fils | M2 |

Composition des 6 fils par moteur :
- M+ et M- : alimentation moteur, gérée en interne par la Hiwonder
- VCC et GND : alimentation du capteur Hall de l'encodeur
- A et B : signaux d'impulsions de l'encodeur

---

## Architecture d'alimentation

```
LiPo 7,4V 2200mAh
    |
    +-- Port PWR Hiwonder (moteurs M1, M2)
        via adaptateur Deans vers JST

Powerbank USB-C
    |
    +-- Raspberry Pi 4B (entrée USB-C)
        |
        +-- Pin 4 (5V)   -> Hiwonder, partie logique
        +-- Pin 2 (5V)   -> HC-SR04 (x3)
        +-- Pin 1 (3,3V) -> MPU6050

ESP32
    |
    +-- USB depuis l'ordinateur (développement)
        Solution future : convertisseur abaisseur 7,4V vers 5V depuis la LiPo
```

**Masse commune obligatoire.** Tous les GND doivent rejoindre le même rail : GND du
Raspberry Pi, GND de la Hiwonder, GND des capteurs, GND des diviseurs de tension, GND de
l'ESP32. Sans masse commune partagée, les niveaux logiques n'ont pas de référence stable
et les bus I2C comme UART échouent de façon intermittente.

---

## Règles de sécurité établies

Une seule source d'alimentation par composant. Alimenter le Raspberry Pi simultanément
par la Powerbank et par la sortie 5V de la Hiwonder provoque un court-circuit.

Ne jamais brancher la LiPo 7,4V directement sur un composant 5V. Un convertisseur
abaisseur réglé et vérifié au multimètre est obligatoire.

Toujours mesurer la tension de sortie d'un convertisseur avant d'y connecter une charge.

Ne pas utiliser de mini breadboards pour la distribution d'alimentation. Leurs contacts
internes peu fiables ont été à l'origine de courts-circuits intermittents. Utiliser les
rails horizontaux de la breadboard principale.
