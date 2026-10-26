"""
Phase 3 — Rotation de 90 degres assistee par gyroscope
Fait pivoter le robot sur place jusqu'a 80 degres mesures, puis coupe les moteurs.
L'inertie termine la rotation aux environs de 90 degres.

Reglage : TURN_SPEED = 7 a ete retenu apres essais. A TURN_SPEED = 12, l'inertie
ajoutait environ 22 degres apres la coupure, avec une variabilite trop importante.
A vitesse reduite, le depassement est d'environ 10 degres et reproductible.

Usage :
    python3 turn_90.py           # rotation gauche
    python3 turn_90.py right     # rotation droite
"""

import smbus2
import time
import sys

HIWONDER_ADDR = 0x34
MPU6050_ADDR  = 0x68

MOTOR_TYPE_ADDR             = 20
MOTOR_ENCODER_POLARITY_ADDR = 21
MOTOR_FIXED_SPEED_ADDR      = 51

PWR_MGMT_1  = 0x6B
GYRO_CONFIG = 0x1B
GYRO_ZOUT_H = 0x47

GYRO_SCALE  = 131.0
CAL_SAMPLES = 200
TURN_SPEED  = 7
CUTOFF_DEG  = 80.0
LOOP_PERIOD = 0.02

bus = smbus2.SMBus(1)
bus.write_byte_data(HIWONDER_ADDR, MOTOR_TYPE_ADDR, 3)
time.sleep(0.1)
bus.write_byte_data(HIWONDER_ADDR, MOTOR_ENCODER_POLARITY_ADDR, 0)
time.sleep(0.1)
bus.write_byte_data(MPU6050_ADDR, PWR_MGMT_1, 0x00)
time.sleep(0.1)
bus.write_byte_data(MPU6050_ADDR, GYRO_CONFIG, 0x00)
time.sleep(0.1)


def read_gyro_z():
    high = bus.read_byte_data(MPU6050_ADDR, GYRO_ZOUT_H)
    low  = bus.read_byte_data(MPU6050_ADDR, GYRO_ZOUT_H + 1)
    raw  = (high << 8) | low
    return raw - 65536 if raw >= 32768 else raw


def set_speed(left, right):
    bus.write_i2c_block_data(HIWONDER_ADDR, MOTOR_FIXED_SPEED_ADDR,
                             [left, right, 0, 0])


def stop():
    for _ in range(3):
        set_speed(0, 0)
        time.sleep(0.01)


direction = 'right' if len(sys.argv) > 1 and sys.argv[1].lower() == 'right' else 'left'

print(f"Calibration gyroscope ({CAL_SAMPLES} echantillons)...")
bias = sum(read_gyro_z() for _ in range(CAL_SAMPLES)) / CAL_SAMPLES
print(f"Biais : {bias:.2f} LSB")

if direction == 'left':
    left_cmd, right_cmd = -TURN_SPEED, TURN_SPEED
else:
    left_cmd, right_cmd = TURN_SPEED, -TURN_SPEED

print(f"Rotation vers la {direction}...")

angle_deg = 0.0
prev_time = time.time()
set_speed(left_cmd, right_cmd)

# La valeur absolue est indispensable : le gyroscope retourne des valeurs negatives
# pour une rotation gauche sur ce montage. Une condition sans abs() ne se termine
# jamais dans ce sens de rotation.
while abs(angle_deg) < CUTOFF_DEG:
    now = time.time()
    dt  = now - prev_time
    prev_time = now
    angle_deg += (read_gyro_z() - bias) / GYRO_SCALE * dt
    print(f"Angle : {angle_deg:.1f} deg", end='\r')
    time.sleep(LOOP_PERIOD)

stop()
print(f"\nMoteurs coupes a {angle_deg:.1f} deg (seuil {CUTOFF_DEG} deg)")
print("Angle final attendu apres inertie : environ 90 deg")
