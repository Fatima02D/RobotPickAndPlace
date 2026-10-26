"""
Phase 2 — Reception des commandes Xbox
S'execute sur le Raspberry Pi. Lit les trames UART envoyees par l'ESP32 et
transmet les consignes de vitesse au module Hiwonder via I2C.

Le robot ne se deplace que tant que ce script tourne.
Arret : Ctrl+C ou fermeture de la session SSH.

Branchements UART (doivent correspondre a main.cpp) :
    RPi Pin 8  (TX, GPIO14) -> ESP32 GPIO27 (RX)
    RPi Pin 10 (RX, GPIO15) -> ESP32 GPIO17 (TX)
    RPi Pin 14 (GND)        -> ESP32 GND

Usage :
    python3 xbox_receiver.py
"""

import serial
import smbus2
import time

UART_PORT = '/dev/ttyS0'
UART_BAUD = 115200

I2C_ADDR                    = 0x34
MOTOR_TYPE_ADDR             = 20
MOTOR_ENCODER_POLARITY_ADDR = 21
MOTOR_FIXED_SPEED_ADDR      = 51

# Securite : arret des moteurs si aucune trame valide recue dans cet intervalle
FAILSAFE_TIMEOUT = 0.2

ser = serial.Serial(UART_PORT, UART_BAUD, timeout=0.05)
bus = smbus2.SMBus(1)
bus.write_byte_data(I2C_ADDR, MOTOR_TYPE_ADDR, 3)
time.sleep(0.1)
bus.write_byte_data(I2C_ADDR, MOTOR_ENCODER_POLARITY_ADDR, 0)
time.sleep(0.1)


def set_speed(left, right):
    try:
        bus.write_i2c_block_data(I2C_ADDR, MOTOR_FIXED_SPEED_ADDR,
                                 [left, right, 0, 0])
        return True
    except OSError:
        return False


def stop():
    for _ in range(3):
        if set_speed(0, 0):
            return
        time.sleep(0.01)


print("Robot pret — bougez le joystick de la manette.")

last_left  = 0
last_right = 0
last_valid = time.time()
last_print = 0

try:
    while True:
        # Vide le tampon UART et ne garde que la trame la plus recente.
        # Sans cette purge, la latence s'accumule : l'ESP32 emet a 50 Hz alors que
        # le traitement I2C et l'affichage SSH sont plus lents, ce qui provoque un
        # decalage croissant entre la commande et le mouvement.
        latest_line = None
        while ser.in_waiting:
            raw = ser.readline()
            try:
                decoded = raw.decode('utf-8').strip()
                if decoded:
                    latest_line = decoded
            except UnicodeDecodeError:
                pass

        if latest_line:
            parts = latest_line.split(',')
            if len(parts) == 2:
                try:
                    left  = max(-100, min(100, int(parts[0])))
                    right = max(-100, min(100, int(parts[1])))
                    if left != last_left or right != last_right:
                        set_speed(left, right)
                        last_left, last_right = left, right
                    last_valid = time.time()
                except ValueError:
                    pass

        if time.time() - last_valid > FAILSAFE_TIMEOUT:
            if last_left != 0 or last_right != 0:
                stop()
                last_left = last_right = 0

        now = time.time()
        if now - last_print > 0.3:
            print(f"G : {last_left:4d}   D : {last_right:4d}")
            last_print = now

        time.sleep(0.005)

except KeyboardInterrupt:
    stop()
    print("Arrete.")
