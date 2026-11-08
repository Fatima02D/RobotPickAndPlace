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

**Trois fils seulement. La broche 5V du port I2C ne se branche à rien.**

| Pin physique RPi | Fonction | Pin Hiwonder |
|---|---|---|
| Pin 3 | SDA (GPIO2) | SDA |
| Pin 5 | SCL (GPIO3) | SCL |
| Pin 6 | GND | GND |

La broche étiquetée 5V du port I2C de la Hiwonder a mesuré 7V sur la première carte,
batterie seule raccordée : son régulateur interne était en court-circuit, entrée sur
sortie. Reliée au Pin 4 du Raspberry Pi, elle a détruit la carte et, rétrospectivement,
le premier Raspberry Pi du projet. Voir `troubleshooting.md`, F1.

La Hiwonder tire son alimentation logique de son port PWR. Elle n'a besoin d'aucune
alimentation venant du Raspberry Pi.

**Protocole de première mise sous tension d'une carte neuve.** LiPo raccordée au port PWR,
rien d'autre connecté, mesure au multimètre sur le port I2C :

| Mesure | Verdict |
|---|---|
| Broche 5V contre GND : environ 5,0V | Carte saine |
| Broche 5V contre GND : environ 7V | Régulateur défectueux, retourner la carte |
| SDA et SCL contre GND : quelques centaines de mV | Lignes de signal saines |

### RPi vers MPU6050 (I2C, même bus)

| Pin physique RPi | Fonction | Pin MPU6050 |
|---|---|---|
| Pin 3 | SDA | SDA |
| Pin 5 | SCL | SCL |
| Pin 1 | 3,3V | VCC |
| Pin 9 | GND | GND |

Le VCC du MPU6050 reste sur le Pin 1 du Raspberry Pi, jamais sur le convertisseur
abaisseur. Alimenté depuis le convertisseur, le capteur disparaissait du bus : ses
résistances de tirage internes sont reliées à VCC_IN, et une alimentation à une tension
différente de celle du maître fausse les niveaux logiques du bus.

Les deux appareils partagent le même bus I2C. Leurs adresses distinctes (0x34 et 0x68)
permettent au Raspberry Pi de les distinguer sans conflit.

### RPi vers ESP32 (UART)

| Pin physique RPi | Fonction | Pin ESP32 |
|---|---|---|
| Pin 8 | TX (GPIO14) | GPIO2 (RX) |
| Pin 10 | RX (GPIO15) | GPIO17 (TX) |
| Pin 14 | GND | GND |

Les fils sont croisés : la sortie de l'un rejoint l'entrée de l'autre. Logique 3,3V des
deux côtés, aucun adaptateur de niveau requis. La masse commune est obligatoire : sans
référence partagée, les niveaux logiques n'ont aucun sens et la liaison échoue de façon
intermittente.

Dans l'état actuel du projet, seul le fil GPIO17 vers Pin 10 transporte des données :
l'ESP32 émet, le Raspberry Pi écoute et ne répond rien.

**Broches à ne pas utiliser sur l'ESP32-S3.** GPIO26 à GPIO32 sont câblées en interne
vers la mémoire flash et la PSRAM. Les configurer en GPIO fait planter la puce au
premier accès flash : redémarrage en boucle, sans aucune sortie série. GPIO27 a été
essayé pour la réception et a produit exactement ce symptôme. Voir
`troubleshooting.md`, G1.

GPIO2 avait été écarté au motif qu'il s'agit d'une broche de configuration. C'est vrai
sur l'ESP32 classique, pas sur le S3, dont les strapping pins sont GPIO0, GPIO3, GPIO45
et GPIO46.

### Protocole UART

Une trame par cycle, à 50 Hz, de l'ESP32 vers le Raspberry Pi :

```
M,L,R\n
```

| Champ | Signification |
|---|---|
| M | Mode : 0 arrêt, 1 téléopération, 2 autonome |
| L | Consigne chenille gauche, -100 à 100 |
| R | Consigne chenille droite, -100 à 100 |

En mode arrêt et en mode autonome, L et R valent toujours 0 : c'est le Raspberry Pi qui
calcule les consignes en autonome. Le champ reste présent pour que le format soit
unique, ce qui simplifie l'analyseur.

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
Powerbank USB-C
    |
    +-- Raspberry Pi 4B (entrée USB-C)
        |
        +-- Pin 2 (5V)   -> HC-SR04 (x3)
        +-- Pin 1 (3,3V) -> MPU6050

LiPo 7,4V 2200mAh
    |
    +-- Port PWR Hiwonder (logique + moteurs M1, M2)
    |   via adaptateur Deans vers JST, en direct
    |
    +-- Convertisseur abaisseur LM2596, réglé à 5,0V
        |
        +-- ESP32
        +-- OUT- rejoint le rail de masse commune
```

Le Raspberry Pi est alimenté par la Powerbank via son entrée USB-C, jamais par ses
broches GPIO. Injecter du 5V sur le Pin 2 ou le Pin 4 contourne le fusible réarmable
d'entrée, qui est la seule protection de la carte contre une surtension.

La LiPo ne traverse jamais une plaque d'essai avant la Hiwonder. Les rails d'une plaque
tiennent environ 1A, contre 1 à 3A d'appel de courant au démarrage des moteurs.

Le convertisseur est réglé à 5,0V et la tension mesurée **à vide**, avant d'y raccorder
quoi que ce soit. Une valeur plus basse ne suffit pas : le régulateur interne de l'ESP32
a besoin d'une marge au-dessus de 3,3V pour fonctionner, et 3,3V en entrée de sa broche
5V ne le démarre pas.

La sortie négative du convertisseur rejoint le rail de masse commune. Son omission est à
l'origine de la corruption de la liaison UART en Phase 2.

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

Mesurer la broche d'alimentation d'un module tiers avant de la raccorder, même et surtout
lorsqu'elle est étiquetée. L'étiquette décrit l'intention du concepteur, pas l'état du
composant.

### Liste de vérification avant mise sous tension

1. La broche 5V du port I2C de la Hiwonder n'est reliée à rien.
2. La LiPo rejoint le port PWR en direct, sans plaque d'essai intermédiaire.
3. Le VCC du MPU6050 est sur le Pin 1 du Raspberry Pi.
4. Le convertisseur est réglé à 5,0V, mesuré à vide.
5. La sortie négative du convertisseur est sur le rail de masse commune.
6. Le Raspberry Pi est alimenté par sa prise USB-C, et par elle seule.
