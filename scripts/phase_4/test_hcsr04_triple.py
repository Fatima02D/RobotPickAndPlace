"""
Phase 4 — Validation des trois capteurs HC-SR04
Lit les trois capteurs ultrason et affiche les distances mesurees.

Branchements :
    Capteur gauche : TRIG = GPIO23 (Pin 16)   ECHO = GPIO24 (Pin 18)
    Capteur centre : TRIG = GPIO17 (Pin 11)   ECHO = GPIO27 (Pin 13)
    Capteur droit  : TRIG = GPIO22 (Pin 15)   ECHO = GPIO26 (Pin 37)

    VCC (x3) -> RPi Pin 2 (5V)
    GND (x3) -> RPi Pin 9 ou Pin 14 (GND)

Chaque ligne ECHO passe par un diviseur 1 kOhm / 2 kOhm pour ramener le signal
de 5V a 3,33V, compatible avec les GPIO du Raspberry Pi.

Usage :
    python3 test_hcsr04_triple.py
"""

import RPi.GPIO as GPIO
import time

CAPTEURS = {
    'Gauche': {'TRIG': 23, 'ECHO': 24},
    'Centre': {'TRIG': 17, 'ECHO': 27},
    'Droite': {'TRIG': 22, 'ECHO': 26},
}

GPIO.setmode(GPIO.BCM)
for c in CAPTEURS.values():
    GPIO.setup(c['TRIG'], GPIO.OUT)
    GPIO.setup(c['ECHO'], GPIO.IN)
    GPIO.output(c['TRIG'], False)

print("Initialisation OK")
time.sleep(0.5)


def lire_distance(trig, echo):
    """Retourne la distance en cm, ou None si aucune mesure valide."""
    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    t = time.time()
    while GPIO.input(echo) == 0:
        if time.time() - t > 0.05:
            return None
    t_debut = time.time()

    while GPIO.input(echo) == 1:
        if time.time() - t_debut > 0.05:
            return None

    # 17150 = vitesse du son (34300 cm/s) divisee par 2 (aller-retour)
    d = (time.time() - t_debut) * 17150
    return round(d, 1) if d < 400 else None


print("Lecture en cours — passez la main devant chaque capteur")
print("Ctrl+C pour arreter\n")

try:
    while True:
        resultats = {}
        for nom, pins in CAPTEURS.items():
            d = lire_distance(pins['TRIG'], pins['ECHO'])
            resultats[nom] = f"{d:.1f}cm" if d is not None else "---"
            time.sleep(0.02)  # evite les interferences entre capteurs

        print(f"G : {resultats['Gauche']:8s}  "
              f"C : {resultats['Centre']:8s}  "
              f"D : {resultats['Droite']:8s}", end='\r')
        time.sleep(0.1)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("\nArrete.")
