"""
Phase 3 — Asservissement de cap par gyroscope
Fait avancer le robot en ligne droite en corrigeant sa trajectoire a partir de la
mesure de cap du gyroscope MPU6050.

Performance mesuree sur ce robot :
    Sans correction              : 11,5 cm de deviation sur 2 m
    Avec rampe de demarrage      : 5 a 7 cm
    Avec asservissement KP=0,7   : environ 1 cm

Usage :
    python3 heading_control.py
"""

import smbus2
import struct
import math
import time

HIWONDER_ADDR = 0x34
MPU6050_ADDR  = 0x68

MOTOR_TYPE_ADDR             = 20
MOTOR_ENCODER_POLARITY_ADDR = 21
MOTOR_FIXED_SPEED_ADDR      = 51
MOTOR_ENCODER_TOTAL_ADDR    = 60

PWR_MGMT_1  = 0x6B
GYRO_CONFIG = 0x1B
GYRO_ZOUT_H = 0x47

# Constantes mesurees empiriquement sur ce robot
METRES_PAR_PULSE = 1.05e-4
ENTRAXE_EFF      = 0.219

BASE_SPEED       = 20     # consigne en regime non sature
RAMP_STEPS       = 10
RAMP_DELAY       = 0.05
KP               = 0.7
ALPHA            = 0.98
LOOP_PERIOD      = 0.05   # 20 Hz
GYRO_SCALE       = 131.0
CAL_SAMPLES      = 200
MAX_DELTA_PULSES = 500    # filtre de plausibilite sur les increments encodeurs

bus = smbus2.SMBus(1)
bus.write_byte_data(HIWONDER_ADDR, MOTOR_TYPE_ADDR, 3)
time.sleep(0.1)
bus.write_byte_data(HIWONDER_ADDR, MOTOR_ENCODER_POLARITY_ADDR, 0)
time.sleep(0.1)
bus.write_byte_data(MPU6050_ADDR, PWR_MGMT_1, 0x00)
time.sleep(0.1)
bus.write_byte_data(MPU6050_ADDR, GYRO_CONFIG, 0x00)
time.sleep(0.1)


def read_encoders():
    raw = bus.read_i2c_block_data(HIWONDER_ADDR, MOTOR_ENCODER_TOTAL_ADDR, 16)
    m1, m2, _, _ = struct.unpack('<iiii', bytes(raw))
    return m1, m2


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


print(f"Calibration gyroscope ({CAL_SAMPLES} echantillons) — robot immobile...")
gyro_bias = sum(read_gyro_z() for _ in range(CAL_SAMPLES)) / CAL_SAMPLES
print(f"Biais gyroscope : {gyro_bias:.2f} LSB")

# La rampe de demarrage evite le patinage initial des chenilles, qui fausse
# l'odometrie et provoque une deviation importante des le depart.
print("Rampe de demarrage...")
for step in range(1, RAMP_STEPS + 1):
    v = int(BASE_SPEED * step / RAMP_STEPS)
    set_speed(v, v)
    time.sleep(RAMP_DELAY)

x = y = theta = 0.0
prev_left, prev_right = read_encoders()
prev_time = time.time()

print("Asservissement actif. Ctrl+C pour arreter.")

try:
    while True:
        now = time.time()
        dt  = now - prev_time
        prev_time = now

        enc_left, enc_right = read_encoders()
        dl_raw = enc_left  - prev_left
        dr_raw = enc_right - prev_right
        prev_left, prev_right = enc_left, enc_right

        if abs(dl_raw) > MAX_DELTA_PULSES or abs(dr_raw) > MAX_DELTA_PULSES:
            time.sleep(LOOP_PERIOD)
            continue

        d_left  = dl_raw * METRES_PAR_PULSE
        d_right = dr_raw * METRES_PAR_PULSE
        d_theta_enc = (d_right - d_left) / ENTRAXE_EFF

        omega        = (read_gyro_z() - gyro_bias) / GYRO_SCALE
        d_theta_gyro = math.radians(omega * dt)

        # Filtre complementaire : le gyroscope domine car il n'est pas affecte par
        # le patinage des chenilles, contrairement aux encodeurs.
        d_theta  = ALPHA * d_theta_gyro + (1.0 - ALPHA) * d_theta_enc
        d_center = (d_left + d_right) / 2.0

        theta += d_theta
        x     += d_center * math.cos(theta)
        y     += d_center * math.sin(theta)

        # Correction proportionnelle vers le cap zero
        correction = KP * (-theta)
        left_cmd   = max(-100, min(100, int(BASE_SPEED + correction)))
        right_cmd  = max(-100, min(100, int(BASE_SPEED - correction)))
        set_speed(left_cmd, right_cmd)

        print(f"x:{x*100:6.1f}cm  y:{y*100:6.1f}cm  "
              f"cap:{math.degrees(theta):6.1f}deg  "
              f"G:{left_cmd:4d} D:{right_cmd:4d}")

        time.sleep(LOOP_PERIOD)

except KeyboardInterrupt:
    stop()
    print(f"\nPose finale : x={x*100:.1f}cm  y={y*100:.1f}cm  "
          f"cap={math.degrees(theta):.1f}deg")
