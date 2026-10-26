# Phase 2 — Téléopération Xbox

**Période :** Juin — Juillet 2026
**Prérequis :** Phase 1 validée (I2C RPi vers Hiwonder opérationnel)

---

## Objectif

Piloter le robot à distance au moyen d'une manette Xbox. La manette communique en
Bluetooth avec un ESP32, lequel transmet les consignes au Raspberry Pi par liaison
série. Le Raspberry Pi convertit ces consignes en commandes moteur et les transmet au
module Hiwonder par le bus I2C.

Critères de complétion :

- Appairage Bluetooth stable entre la manette et l'ESP32
- Les joysticks contrôlent la vitesse et la direction des chenilles
- Latence commande vers mouvement inférieure à 100 ms
- Le robot s'arrête de manière fiable lorsque le joystick est relâché
- Comportement prévisible et reproductible

---

## Architecture retenue

```
Manette Xbox
    |  Bluetooth (NimBLE)
ESP32 TTGO T-Display
    |  UART 115200 bauds
Raspberry Pi 4B
    |  I2C, adresse 0x34
Module Hiwonder Encoder Motor V1.4
    |
Moteurs M1 (gauche) et M2 (droite)
```

Le choix d'un microcontrôleur intermédiaire pour le Bluetooth, plutôt que d'utiliser le
Bluetooth intégré du Raspberry Pi, est hérité d'un projet antérieur (GEI-1049) où cette
architecture avait été validée. Elle présente deux avantages : la pile Bluetooth de la
manette Xbox est capricieuse sous Linux, et déporter cette contrainte sur l'ESP32 libère
le Raspberry Pi pour les tâches de plus haut niveau prévues aux phases ultérieures.

---

## Répartition logicielle

Deux programmes, sur deux machines distinctes.

**`main.cpp`** — C++ avec framework Arduino, exécuté sur l'ESP32. Compilé et téléversé
depuis VS Code avec PlatformIO. Deux tâches FreeRTOS : `XboxTask` (lecture manette et
émission UART, 50 Hz) et `DisplayTask` (rafraîchissement de l'écran TFT, 5 Hz).

**`xbox_receiver.py`** — Python, exécuté sur le Raspberry Pi. Lancement manuel en SSH.
Lit la liaison série, décode les consignes, écrit sur le bus I2C.

Le robot ne se déplace que si `xbox_receiver.py` est en cours d'exécution. L'arrêt du
script, ou la fermeture de la session SSH, immobilise le robot.

---

## Configuration UART

| ESP32 TTGO | Raspberry Pi | Signal |
|---|---|---|
| GPIO17 | Pin 10 (GPIO15) | ESP32 TX vers RPi RX |
| GPIO27 | Pin 8 (GPIO14) | ESP32 RX depuis RPi TX |
| GND | Pin 6 | Masse commune, obligatoire |

Initialisation côté ESP32 :

```cpp
Serial2.begin(115200, SERIAL_8N1, 27, 17);
```

Les deux cartes fonctionnent en logique 3,3 V. Aucun adaptateur de niveau n'est requis.

### Sélection des broches : deux contraintes du TTGO T-Display

Le choix de GPIO27 pour la réception n'est pas arbitraire. Deux broches, apparemment
disponibles, ne le sont pas sur cette carte.

**GPIO16 est indisponible.** C'est la broche de réception par défaut de `Serial2` sur un
ESP32 standard, mais sur le T-Display elle est câblée au signal TFT_DC de l'écran.
L'utiliser pour l'UART entrerait en conflit avec l'affichage.

**GPIO2 est une broche de configuration (strapping pin).** Son état au moment du
démarrage participe à la sélection du mode de boot. Or, une ligne UART au repos est
maintenue à l'état haut par l'émetteur. Si le Raspberry Pi est déjà alimenté lorsque
l'ESP32 démarre, sa ligne TX maintient GPIO2 dans un état susceptible d'empêcher le
démarrage de l'ESP32.

GPIO27 ne présente aucune de ces deux contraintes : ni broche de configuration, ni
utilisée par l'écran.

Note : le câblage a fonctionné pendant une partie des essais avec GPIO2 en réception.
Ce n'est pas une preuve d'innocuité. Ce type de défaut se manifeste de façon
intermittente, en fonction de l'ordre de mise sous tension des deux cartes.

---

## Protocole de communication

L'ESP32 émet une ligne de texte par cycle, à 50 Hz :

```
<vitesse_gauche>,<vitesse_droite>\n
```

Les deux valeurs sont des entiers dans l'intervalle [-100, 100]. Format volontairement
minimal : lisible directement dans un moniteur série, ce qui simplifie le diagnostic.

Côté Raspberry Pi, les consignes sont écrites au registre 51
(`MOTOR_FIXED_SPEED_ADDR`) sous forme d'un bloc de quatre octets, le module Hiwonder
gérant quatre ports moteur dont deux sont utilisés.

| Registre | Adresse | Rôle |
|---|---|---|
| `MOTOR_TYPE_ADDR` | 20 | Type de moteur (valeur 3) |
| `MOTOR_ENCODER_POLARITY_ADDR` | 21 | Polarité des encodeurs |
| `MOTOR_FIXED_SPEED_ADDR` | 51 | Consigne de vitesse, quatre moteurs |

---

## Traitement du joystick

Trois traitements successifs sont appliqués aux valeurs brutes de la manette.

### Calibration du centre

Un joystick au repos ne renvoie pas zéro. La valeur de repos varie d'une manette à
l'autre et dérive avec l'usure. Le centre réel est donc mesuré au démarrage, par moyenne
sur trente échantillons.

Une garde est appliquée : si le centre calculé s'écarte de plus de 8000 de la valeur
médiane théorique, la calibration est rejetée et recommencée. Sans cette garde, une
calibration effectuée alors que le joystick est poussé produirait un centre faux, et le
robot partirait seul au démarrage.

### Zone morte

La valeur de repos fluctue autour du centre calibré. Sans filtrage, cette fluctuation
produit une consigne moteur non nulle alors que l'opérateur ne touche à rien.

La zone morte est appliquée sur chaque axe brut, avant le mélange des consignes. Cet
ordre est essentiel : appliquée après le mélange, un résidu sur l'axe horizontal
survivrait au calcul et ferait pivoter le robot en continu.

```cpp
if (abs(joyV) < DEADZONE) joyV = 0;
if (abs(joyH) < DEADZONE) joyH = 0;
```

Valeur initiale : 2500 sur une plage de 65536, soit 3,8 % de la course. Insuffisante —
voir la section Incidents.
Valeur retenue : 6000, soit 9,2 % de la course.

### Mélange différentiel

L'axe vertical commande l'avance, l'axe horizontal la rotation. Les deux se combinent :

```cpp
int linear  = map(joyV, -32768, 32768, -100, 100);
int angular = map(joyH, -32768, 32768, -100, 100);

leftSpeed  = constrain(linear - angular, -100, 100);
rightSpeed = constrain(linear + angular, -100, 100);
```

L'axe vertical de la manette Xbox est inversé par rapport à la convention attendue :
pousser vers l'avant fait décroître la valeur brute. Le signe est corrigé à la source :

```cpp
int32_t joyV = -(rawV - centerV);
```

---

## Affichage embarqué

L'écran TFT intégré au T-Display affiche en continu l'état du système : date et heure
synchronisées par NTP, état de la connexion Bluetooth, état de la calibration, niveau de
batterie de la manette, et consignes appliquées aux deux moteurs.

Le rendu passe par un sprite en mémoire, poussé vers l'écran en une seule opération. Un
dessin direct ligne par ligne produirait un scintillement visible.

L'affichage des consignes moteur s'est révélé l'outil de diagnostic le plus utile de la
phase : il permet de constater immédiatement si une déviation du robot provient d'une
consigne asymétrique ou d'un déséquilibre mécanique, sans passer par le terminal.

---

## Incidents et résolutions

### Masse commune absente ou intermittente

**Symptôme.** Échec complet de la liaison UART, ou réception de caractères corrompus
(erreurs de décodage UTF-8).

**Cause.** Absence de masse commune entre l'ESP32 et le Raspberry Pi, ou contact
défectueux sur cette liaison.

**Résolution.** Établissement d'une liaison de masse dédiée, en connexion directe.

Ce défaut est réapparu ultérieurement sur le bus I2C, avec un mécanisme identique. Il
constitue le mode de défaillance récurrent de ce montage.

### Alimentation de l'ESP32 : sortie 5 V du Hiwonder inexploitable

**Symptôme.** L'ESP32 ne démarre pas lorsqu'il est alimenté par la sortie 5 V du module
Hiwonder.

**Diagnostic.** Tension mesurée à vide sur cette sortie : 2,7 V. Le régulateur du module
ne fournit pas la tension annoncée.

**Résolution.** Alimentation de l'ESP32 par le port USB pendant les essais. Un étage
d'alimentation dédié est nécessaire pour l'autonomie complète du robot.

### Zone morte insuffisante

**Symptôme.** Les moteurs poursuivent leur rotation après relâchement du joystick.

**Diagnostic.** La zone morte, fixée à 2500 sur une plage de 65536, était inférieure à
la dérive résiduelle de l'axe horizontal au repos. Une consigne de rotation non nulle
était donc émise en permanence.

**Résolution.** Zone morte portée à 6000, vérifiée par observation des valeurs brutes au
moniteur série, joystick relâché.

### Commandes d'arrêt perdues

**Symptôme.** Le terminal affiche `Left: 0, Right: 0`, mais les moteurs continuent de
tourner.

**Diagnostic.** La consigne nulle était correctement calculée, mais l'écriture I2C
échouait par intermittence en raison du défaut de masse. Le module Hiwonder conservait
alors la dernière consigne valide reçue.

**Résolution.** Deux mécanismes ajoutés côté Raspberry Pi.

La commande d'arrêt est réémise jusqu'à confirmation d'écriture. Une commande d'arrêt
perdue laisse un système mobile en mouvement : elle ne peut pas être traitée comme une
commande ordinaire.

Un dispositif de repli indépendant arrête les moteurs en l'absence de trame UART pendant
plus de 200 ms. Sans ce dispositif, une interruption de la liaison — manette éteinte,
ESP32 redémarré, câble débranché — laissait les moteurs à leur dernière consigne
indéfiniment.

```python
def stop():
    """Réessaie jusqu'à confirmation."""
    for _ in range(3):
        if set_speed(0, 0):
            return
        time.sleep(0.01)
```

---

## Résultat

La téléopération est fonctionnelle. Le robot répond aux quatre directions, la latence est
imperceptible à l'usage, et l'arrêt est fiable.

Une déviation systématique en ligne droite subsiste. Elle n'est pas d'origine logicielle :
sous consigne symétrique, le robot dévie constamment du même côté. Ce phénomène est
caractérisé en Phase 3.

---

## Enseignements

**La masse commune est le point de défaillance dominant de ce montage.** Elle a provoqué
l'échec de la liaison UART, puis celui du bus I2C, puis la perte de commandes d'arrêt.
Dans les trois cas, le symptôme initial pointait vers une cause logicielle, et le
diagnostic réel était électrique. Une liaison de masse défectueuse ne produit pas une
panne franche mais un comportement intermittent, ce qui la rend particulièrement
coûteuse à diagnostiquer.

**L'étiquette d'une broche ne suffit pas.** GPIO2 est disponible sur le brochage, et son
usage en réception UART fonctionne — jusqu'à ce qu'il ne fonctionne plus, selon l'ordre
de mise sous tension. La consultation du schéma de la carte précède son câblage.

**Une commande d'arrêt exige un traitement particulier.** Un système mobile dont
l'immobilisation dépend d'une trame susceptible d'être perdue n'est pas sûr. La
réémission jusqu'à confirmation et le repli sur temporisation ne sont pas des
raffinements optionnels.

---

## Suite

Phase 3 — odométrie. Caractérisation du déséquilibre moteur, puis intégration de pose par
odométrie différentielle, quantification de la dérive angulaire, et décision argumentée
sur l'ajout de la centrale inertielle MPU6050.
