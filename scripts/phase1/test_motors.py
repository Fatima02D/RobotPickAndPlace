"""
Phase 1 — Test moteurs de base
Valide la communication I2C avec le module Hiwonder (adresse 0x34).
A executer directement sur le Raspberry Pi via SSH.

Usage :
    python3 test_motors.py

Le robot doit etre souleve, chenilles dans le vide, pendant ce test.
"""

import smbus2
import time

I2C_ADDR                    = 0x34
MOTOR_TYPE_ADDR             = 20
MOTOR_ENCODER_POLARITY_ADDR = 21
MOTOR_FIXED_SPEED_ADDR      = 51

bus = smbus2.SMBus(1)
bus.write_byte_data(I2C_ADDR, MOTOR_TYPE_ADDR, 3)
time.sleep(0.1)
bus.write_byte_data(I2C_ADDR, MOTOR_ENCODER_POLARITY_ADDR, 0)
time.sleep(0.1)


def set_speed(left, right):
    bus.write_i2c_block_data(I2C_ADDR, MOTOR_FIXED_SPEED_ADDR,
                             [left & 0xFF, right & 0xFF, 0, 0])


print("Test moteurs — le robot doit etre souleve du sol.")
time.sleep(1)

sequence = [
    ("Avancer",       50,  50),
    ("Arret",          0,   0),
    ("Reculer",      -50, -50),
    ("Arret",          0,   0),
    ("Tourner gauche", -50, 50),
    ("Arret",          0,   0),
    ("Tourner droite", 50, -50),
    ("Arret",          0,   0),
]

for label, left, right in sequence:
    print(label)
    set_speed(left, right)
    time.sleep(2 if left != 0 or right != 0 else 1)

print("Test termine.")
