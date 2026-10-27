#!/usr/bin/env python3
"""
Selecteur de mode — Phase 4.

S'execute sur le Raspberry Pi. Lit les trames UART de l'ESP32, qui portent le
mode choisi a la manette Xbox, et oriente la commande des moteurs en
consequence :

    Mode 0  ARRET          moteurs a zero
    Mode 1  TELEOPERATION   consignes du joystick, relayees telles quelles
    Mode 2  AUTONOME        consignes calculees ici par la logique d'evitement

C'est ce script qui fait des Phases 2 et 4 un seul systeme plutot que deux
demonstrations separees.

Protocole UART, une trame par cycle a 50 Hz :

    M,L,R\\n

Branchements UART (doivent correspondre a main.cpp) :
    RPi Pin 8  (TX, GPIO14) -> ESP32 GPIO27 (RX)
    RPi Pin 10 (RX, GPIO15) -> ESP32 GPIO17 (TX)
    RPi Pin 14 (GND)        -> ESP32 GND

Boutons de la manette :
    A = teleoperation    B = autonome    Y = arret

Usage :
    python3 mode_receiver.py
"""

import serial
import time
import evitement as ev

# ---------------------------------------------------------------
# Interrupteurs de mise au point
# ---------------------------------------------------------------
# MOTEURS_ACTIFS a False : les consignes sont calculees et affichees mais
# jamais transmises en I2C. C'est le mode de travail tant que le controleur
# moteur de remplacement n'est pas arrive. Passer a True quand il est en place
# et que la broche 5 V de son port I2C a ete mesuree (voir hardware.md).
MOTEURS_ACTIFS = False

# CAPTEURS_ACTIFS a False : le mode autonome renvoie des consignes nulles.
# Utile pour tester la seule bascule de mode, sans les capteurs.
CAPTEURS_ACTIFS = True

# ---------------------------------------------------------------
# Liaison serie
# ---------------------------------------------------------------
UART_PORT = '/dev/ttyS0'
UART_BAUD = 115200

# Securite : si aucune trame valide n'arrive dans cet intervalle, arret.
# La manette ou l'ESP32 peuvent se taire sans prevenir ; l'absence de nouvelle
# n'est jamais interpretee comme "continue comme avant".
FAILSAFE_TIMEOUT = 0.3

# ---------------------------------------------------------------
# Controleur moteur Hiwonder
# ---------------------------------------------------------------
I2C_ADDR                    = 0x34
MOTOR_TYPE_ADDR             = 20
MOTOR_ENCODER_POLARITY_ADDR = 21
MOTOR_FIXED_SPEED_ADDR      = 51

MODE_ARRET    = 0
MODE_TELEOP   = 1
MODE_AUTONOME = 2

NOM_MODE = {
    MODE_ARRET:    "ARRET",
    MODE_TELEOP:   "TELEOPERATION",
    MODE_AUTONOME: "AUTONOME",
}


class Moteurs:
    """
    Acces au controleur moteur, ou simulacre quand MOTEURS_ACTIFS est False.

    Toute la commande des moteurs passe par cet objet. C'est ce qui permet de
    tester l'integralite du selecteur de mode sans materiel, en basculant un
    seul booleen.
    """

    def __init__(self, actifs):
        self.actifs = actifs
        self.bus = None
        if not actifs:
            print("MOTEURS DESACTIVES — consignes calculees mais non transmises")
            return

        import smbus2
        self.bus = smbus2.SMBus(1)
        self.bus.write_byte_data(I2C_ADDR, MOTOR_TYPE_ADDR, 3)
        time.sleep(0.1)
        self.bus.write_byte_data(I2C_ADDR, MOTOR_ENCODER_POLARITY_ADDR, 0)
        time.sleep(0.1)
        print("Controleur moteur initialise a l'adresse 0x{:02x}".format(I2C_ADDR))

    def vitesse(self, gauche, droite):
        if not self.actifs:
            return True
        try:
            self.bus.write_i2c_block_data(
                I2C_ADDR, MOTOR_FIXED_SPEED_ADDR, [gauche, droite, 0, 0])
            return True
        except OSError:
            return False

    def arret(self):
        # Une commande d'arret n'est pas une commande ordinaire : elle est
        # reemise jusqu'a confirmation. Lecon de la Phase 2 (voir
        # troubleshooting.md, C10).
        for _ in range(3):
            if self.vitesse(0, 0):
                return
            time.sleep(0.01)


def main():
    ser = serial.Serial(UART_PORT, UART_BAUD, timeout=0.05)
    moteurs = Moteurs(MOTEURS_ACTIFS)

    logique = None
    if CAPTEURS_ACTIFS:
        print("Initialisation des capteurs...")
        ev.init_capteurs()
        ev.amorcer(time.sleep)
        logique = ev.Evitement()
        print("Capteurs prets")
    else:
        print("CAPTEURS DESACTIVES — le mode autonome renverra 0,0")

    print("\nSelecteur de mode actif.")
    print("Manette : A = teleoperation, B = autonome, Y = arret")
    print("Ctrl+C pour arreter\n")

    mode          = MODE_ARRET
    mode_affiche  = None
    joy_g, joy_d  = 0, 0
    cmd_g, cmd_d  = 0, 0
    etat_auto     = ""
    derniere_trame = time.time()
    dernier_calcul = 0.0
    dernier_print  = 0.0

    try:
        while True:
            # --- Lecture UART, en ne gardant que la trame la plus recente ---
            # Sans cette purge, la latence s'accumule : l'ESP32 emet a 50 Hz
            # alors que le traitement est plus lent, ce qui provoque un decalage
            # croissant entre la commande et le mouvement (Phase 2, C9).
            derniere_ligne = None
            while ser.in_waiting:
                brut = ser.readline()
                try:
                    texte = brut.decode('utf-8').strip()
                    if texte:
                        derniere_ligne = texte
                except UnicodeDecodeError:
                    pass

            if derniere_ligne:
                champs = derniere_ligne.split(',')
                if len(champs) == 3:
                    try:
                        recu  = int(champs[0])
                        joy_g = max(-100, min(100, int(champs[1])))
                        joy_d = max(-100, min(100, int(champs[2])))
                        if recu in NOM_MODE:
                            if recu != mode:
                                # Changement de mode : les moteurs s'arretent
                                # avant toute autre chose, et le verrou
                                # d'evitement repart propre.
                                moteurs.arret()
                                cmd_g = cmd_d = 0
                                if logique is not None:
                                    logique.reinitialiser()
                                print("\n--- MODE : {} ---".format(NOM_MODE[recu]))
                            mode = recu
                            derniere_trame = time.time()
                    except ValueError:
                        pass

            # --- Repli sur temporisation ---
            silence = time.time() - derniere_trame > FAILSAFE_TIMEOUT
            if silence and mode != MODE_ARRET:
                print("\n--- SILENCE UART : repli en ARRET ---")
                mode = MODE_ARRET
                moteurs.arret()
                cmd_g = cmd_d = 0
                if logique is not None:
                    logique.reinitialiser()

            # --- Decision selon le mode ---
            maintenant = time.time()

            if mode == MODE_ARRET:
                if cmd_g != 0 or cmd_d != 0:
                    moteurs.arret()
                cmd_g = cmd_d = 0
                etat_auto = ""

            elif mode == MODE_TELEOP:
                if joy_g != cmd_g or joy_d != cmd_d:
                    moteurs.vitesse(joy_g, joy_d)
                    cmd_g, cmd_d = joy_g, joy_d
                etat_auto = ""

            elif mode == MODE_AUTONOME:
                # La logique tourne a 10 Hz, independamment du debit UART :
                # les capteurs a ultrasons ne peuvent pas etre interroges plus
                # vite sans que les echos se chevauchent.
                if maintenant - dernier_calcul >= ev.LOOP_PERIOD:
                    dernier_calcul = maintenant
                    if logique is not None:
                        g, c, d = ev.lire_tout()
                        nouveau_g, nouveau_d, etat_auto = logique.consignes(g, c, d)
                        if nouveau_g != cmd_g or nouveau_d != cmd_d:
                            moteurs.vitesse(nouveau_g, nouveau_d)
                            cmd_g, cmd_d = nouveau_g, nouveau_d
                    else:
                        if cmd_g != 0 or cmd_d != 0:
                            moteurs.arret()
                        cmd_g = cmd_d = 0
                        etat_auto = "capteurs desactives"

            # --- Affichage ---
            if maintenant - dernier_print > 0.3 or mode != mode_affiche:
                suffixe = "   " + etat_auto if etat_auto else ""
                print("[{:13s}]  G : {:4d}   D : {:4d}{}".format(
                    NOM_MODE[mode], cmd_g, cmd_d, suffixe))
                dernier_print = maintenant
                mode_affiche  = mode

            time.sleep(0.005)

    except KeyboardInterrupt:
        pass
    finally:
        moteurs.arret()
        ser.close()
        print("\nArrete, moteurs a zero.")


if __name__ == '__main__':
    main()
