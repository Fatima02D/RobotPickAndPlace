"""
Phase 3 — Caracterisation du desequilibre moteur
Mesure le rapport de vitesse entre les deux moteurs sur six points de
fonctionnement (consignes 30, 50 et 80, en marche avant et arriere), trois
essais par point, soit dix-huit essais au total.

Objectif : determiner si une correction en boucle ouverte par coefficient fixe
est defendable, ou si le desequilibre varie selon le point de fonctionnement.

Conclusion tiree de ces mesures : K_RIGHT = 1,0, aucune correction necessaire.
Le desequilibre de 4 % observe initialement avait ete mesure a la consigne 50,
donc en pleine saturation des moteurs. En regime non sature (consignes 10 a 30),
la regulation interne du module Hiwonder equilibre les deux chaines de facon
quasi parfaite.

Usage :
    python3 motor_balance.py

Le robot doit etre au sol, chenilles en contact avec la surface reelle. Un essai
roues en l'air mesurerait le desequilibre a vide, ce qui exclut le patinage et la
friction du sol, deux composantes du phenomene reel.
"""

import smbus2
import struct
import time
import statistics

I2C_ADDR                    = 0x34
MOTOR_TYPE_ADDR             = 20
MOTOR_ENCODER_POLARITY_ADDR = 21
MOTOR_FIXED_SPEED_ADDR      = 51
MOTOR_ENCODER_TOTAL_ADDR    = 60

SPEEDS   = [30, 50, 80]
REPEATS  = 3
DURATION = 3.0

bus = smbus2.SMBus(1)
bus.write_byte_data(I2C_ADDR, MOTOR_TYPE_ADDR, 3)
time.sleep(0.1)
bus.write_byte_data(I2C_ADDR, MOTOR_ENCODER_POLARITY_ADDR, 0)
time.sleep(0.1)


def read_encoders():
    """Quatre compteurs cumules, int32 little-endian, seize octets."""
    raw = bus.read_i2c_block_data(I2C_ADDR, MOTOR_ENCODER_TOTAL_ADDR, 16)
    return struct.unpack('<iiii', bytes(raw))


def set_speed(left, right):
    bus.write_i2c_block_data(I2C_ADDR, MOTOR_FIXED_SPEED_ADDR,
                             [left & 0xFF, right & 0xFF, 0, 0])


def run_trial(speed, duration):
    start = read_encoders()
    set_speed(speed, speed)
    time.sleep(duration)
    set_speed(0, 0)
    time.sleep(0.3)
    end = read_encoders()
    return end[0] - start[0], end[1] - start[1]


results = {}

for speed in SPEEDS:
    for direction in [1, -1]:
        cmd = speed * direction
        ratios = []

        input(f"\nConsigne {cmd:+d} — Entree pour lancer...")

        for i in range(REPEATS):
            d_left, d_right = run_trial(cmd, DURATION)
            if d_left == 0:
                print(f"  Essai {i+1} : encodeur gauche a zero, ignore")
                continue
            ratio = d_right / d_left
            ratios.append(ratio)
            print(f"  Essai {i+1} : G={d_left:6d}  D={d_right:6d}  ratio={ratio:.4f}")
            time.sleep(0.5)

        if ratios:
            mean = statistics.mean(ratios)
            sd   = statistics.stdev(ratios) if len(ratios) > 1 else 0.0
            results[cmd] = (mean, sd, len(ratios))
            print(f"  Moyenne {mean:.4f}   ecart-type {sd:.4f}")

print("\n--- Synthese ---")
means = [m for m, _, _ in results.values()]
sds   = [s for _, s, _ in results.values()]

if means:
    spread   = max(means) - min(means)
    worst_sd = max(sds)
    print(f"Ecart entre points de fonctionnement : {spread:.4f}")
    print(f"Ecart-type maximal intra-point       : {worst_sd:.4f}")

    # Critere de viabilite : le desequilibre doit etre reproductible (faible
    # ecart-type) et constant sur la plage (faible ecart entre points). Si la
    # variation entre consignes n'est pas distinguable du bruit de mesure, un
    # coefficient unique est justifie.
    if spread < 0.02 and worst_sd < 0.015:
        k = 1.0 / statistics.mean(means)
        print("\nDesequilibre constant. Correction en boucle ouverte defendable.")
        print(f"K_RIGHT = {k:.4f}")
    else:
        print("\nDesequilibre variable selon le point de fonctionnement.")
        print("Une correction par coefficient fixe n'est pas defendable.")
