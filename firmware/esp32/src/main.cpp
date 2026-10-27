// Robot Mobile Autonome — Firmware ESP32
// Carte : LilyGo T-Display S3
//
// Role : reception manette Xbox via Bluetooth BLE, selection du mode de
//        fonctionnement, transmission des consignes au Raspberry Pi via UART,
//        affichage d'etat sur ecran TFT.
//
// Branchements UART :
//   GPIO17 (TX) -> RPi Pin 10 (RX)
//   GPIO27 (RX) -> RPi Pin 8  (TX)
//   GND         -> RPi Pin 14 (GND)
//
// Note sur GPIO27 : GPIO2 etait utilise initialement pour le RX mais c'est une
// broche de configuration (strapping pin). La ligne TX du Raspberry Pi maintenue
// haute au demarrage peut empecher l'ESP32 de booter. GPIO27 n'a pas cette
// contrainte.
//
// ===== PROTOCOLE UART =====
//
// Une trame par cycle, a 50 Hz :
//
//     M,L,R\n
//
//   M : mode      0 = ARRET, 1 = TELEOPERATION, 2 = AUTONOME
//   L : consigne chenille gauche,  -100 a 100
//   R : consigne chenille droite,  -100 a 100
//
// En mode ARRET et en mode AUTONOME, L et R valent toujours 0 : c'est le
// Raspberry Pi qui calcule les consignes en autonome. Le champ reste present
// pour que le format de trame soit unique, ce qui simplifie l'analyseur.
//
// ===== SELECTION DU MODE =====
//
//   Bouton A : mode TELEOPERATION
//   Bouton B : mode AUTONOME
//   Bouton Y : ARRET
//
// Choix de trois boutons distincts plutot qu'une bascule sur un seul bouton :
// l'etat demande est toujours explicite. Avec une bascule, une pression non
// enregistree inverse la signification de toutes les suivantes.
//
// Le mode au demarrage est ARRET. Rien ne bouge avant une action deliberee.
// Toute deconnexion de la manette force le retour en ARRET.

#include <Arduino.h>
#include <WiFi.h>
#include <time.h>
#include <TFT_eSPI.h>
#include <XboxSeriesXControllerESP32_asukiaaa.hpp>

// ===== CONFIGURATION =====

#define RPI_TX       17
#define RPI_RX       27
#define PIN_POWER_ON 15

const char* WIFI_SSID = "VOTRE_RESEAU_WIFI";
const char* WIFI_PASS = "VOTRE_MOT_DE_PASSE";

const long GMT_OFFSET_SEC      = -4 * 3600;   // UTC-4 (heure d'ete Quebec)
const int  DAYLIGHT_OFFSET_SEC = 0;

// Zone morte du joystick, sur la plage brute 0-65535 (soit 9,2 % de la course)
const int32_t DEADZONE = 6000;

// Nombre d'echantillons moyennes au demarrage pour trouver le centre du joystick
const int CAL_SAMPLES = 30;

// Garde-fou : rejette la calibration si le centre calcule s'ecarte trop du point
// median theorique (32768). Evite un faux centre si le joystick est pousse pendant
// la phase de calibration.
const int32_t CAL_GUARD = 8000;

// Securite : envoie une commande d'arret si aucune trame n'a ete emise depuis
// cette duree (millisecondes)
const int FAILSAFE_MS = 200;

// ===== MODES =====

enum Mode : uint8_t {
    MODE_ARRET   = 0,
    MODE_TELEOP  = 1,
    MODE_AUTONOME = 2
};

const char* nomMode(uint8_t m) {
    switch (m) {
        case MODE_TELEOP:   return "TELEOPERATION";
        case MODE_AUTONOME: return "AUTONOME";
        default:            return "ARRET";
    }
}

// ===== VARIABLES GLOBALES =====

XboxSeriesXControllerESP32_asukiaaa::Core xboxController;
TFT_eSPI    tft    = TFT_eSPI();
TFT_eSprite sprite = TFT_eSprite(&tft);

volatile int     leftSpeed     = 0;
volatile int     rightSpeed    = 0;
volatile uint8_t mode          = MODE_ARRET;
volatile bool    xboxConnected = false;
volatile uint8_t xboxBattery   = 0;
volatile bool    calibrated    = false;

// ===== TACHE MANETTE XBOX =====

void XboxTask(void *pvParameters) {
    xboxController.begin();
    Serial.println("En attente de la manette Xbox...");

    int32_t sumV = 0, sumH = 0;
    int     calCount = 0;
    int32_t centerV  = 0, centerH = 0;
    unsigned long lastFrameMs = 0;

    // Etat precedent des boutons, pour ne reagir qu'au front montant.
    // Sans cela, un appui maintenu de 200 ms reemettrait le changement de mode
    // dix fois de suite.
    bool prevA = false, prevB = false, prevY = false;

    for (;;) {
        xboxController.onLoop();
        xboxConnected = xboxController.isConnected();

        if (xboxConnected && !xboxController.isWaitingForFirstNotification()) {
            auto &notif = xboxController.xboxNotif;
            xboxBattery = xboxController.battery;

            int32_t rawV = (int32_t)notif.joyLVert;
            int32_t rawH = (int32_t)notif.joyLHori;

            // --- Phase de calibration ---
            if (!calibrated) {
                sumV += rawV;
                sumH += rawH;
                calCount++;
                if (calCount >= CAL_SAMPLES) {
                    int32_t candV = sumV / calCount;
                    int32_t candH = sumH / calCount;
                    if (abs(candV - 32768) < CAL_GUARD &&
                        abs(candH - 32768) < CAL_GUARD) {
                        centerV    = candV;
                        centerH    = candH;
                        calibrated = true;
                        Serial.printf("Calibration OK : centerV=%ld centerH=%ld\n",
                                      centerV, centerH);
                    } else {
                        sumV = 0; sumH = 0; calCount = 0;
                        Serial.println("Calibration rejetee (joystick non centre).");
                    }
                }
                leftSpeed  = 0;
                rightSpeed = 0;
                vTaskDelay(pdMS_TO_TICKS(20));
                continue;
            }

            // --- Selection du mode, sur front montant ---
            bool curA = notif.btnA;
            bool curB = notif.btnB;
            bool curY = notif.btnY;

            if (curY && !prevY) {
                mode = MODE_ARRET;
                Serial.println("Mode -> ARRET");
            } else if (curA && !prevA) {
                mode = MODE_TELEOP;
                Serial.println("Mode -> TELEOPERATION");
            } else if (curB && !prevB) {
                mode = MODE_AUTONOME;
                Serial.println("Mode -> AUTONOME");
            }

            prevA = curA;
            prevB = curB;
            prevY = curY;

            // --- Traitement du joystick ---
            // L'axe vertical Xbox est inverse : pousser vers l'avant diminue la
            // valeur brute
            int32_t joyV = -(rawV - centerV);
            int32_t joyH =   rawH - centerH;

            if (abs(joyV) < DEADZONE) joyV = 0;
            if (abs(joyH) < DEADZONE) joyH = 0;

            int linear  = constrain((int)map(joyV, -32768, 32768, -100, 100),
                                    -100, 100);
            int angular = constrain((int)map(joyH, -32768, 32768, -100, 100),
                                    -100, 100);

            // Le joystick n'est transmis qu'en teleoperation. En autonome, les
            // consignes viennent du Raspberry Pi ; en arret, elles sont nulles.
            if (mode == MODE_TELEOP) {
                leftSpeed  = constrain(linear - angular, -100, 100);
                rightSpeed = constrain(linear + angular, -100, 100);
            } else {
                leftSpeed  = 0;
                rightSpeed = 0;
            }

            String cmd = String(mode) + "," +
                         String(leftSpeed) + "," +
                         String(rightSpeed) + "\n";
            Serial2.print(cmd);
            lastFrameMs = millis();

        } else {
            // Manette deconnectee : retour en arret, et reemission periodique
            // pour que le Raspberry Pi recoive l'ordre meme si une trame se perd.
            calibrated = false;
            mode       = MODE_ARRET;
            leftSpeed  = 0;
            rightSpeed = 0;
            prevA = prevB = prevY = false;
            if (millis() - lastFrameMs > FAILSAFE_MS) {
                Serial2.println("0,0,0");
                lastFrameMs = millis();
            }
        }

        vTaskDelay(pdMS_TO_TICKS(20));  // 50 Hz
    }
}

// ===== TACHE AFFICHAGE =====

void DisplayTask(void *pvParameters) {
    for (;;) {
        sprite.fillSprite(TFT_BLACK);

        struct tm timeinfo;
        char dateStr[32];
        char timeStr[32];
        if (getLocalTime(&timeinfo, 100)) {
            strftime(dateStr, sizeof(dateStr), "%Y-%m-%d", &timeinfo);
            strftime(timeStr, sizeof(timeStr), "%H:%M:%S", &timeinfo);
        } else {
            strcpy(dateStr, "Sync NTP...");
            strcpy(timeStr, "--:--:--");
        }

        int y = 4;
        sprite.setTextDatum(TL_DATUM);

        sprite.setTextColor(TFT_YELLOW, TFT_BLACK);
        sprite.drawString("Robot Mobile Autonome", 5, y, 4);
        y += 32;

        // Le mode est l'information la plus importante a l'ecran : il indique si
        // le robot peut bouger et sous quel controle. Affiche en gros et colore.
        uint16_t couleurMode = TFT_RED;
        if (mode == MODE_TELEOP)   couleurMode = TFT_GREEN;
        if (mode == MODE_AUTONOME) couleurMode = TFT_CYAN;
        sprite.setTextColor(couleurMode, TFT_BLACK);
        sprite.drawString(nomMode(mode), 5, y, 4);
        y += 34;

        sprite.setTextColor(TFT_WHITE, TFT_BLACK);
        sprite.drawString(String(dateStr) + "  " + String(timeStr), 5, y, 2);
        y += 22;

        sprite.setTextColor(xboxConnected ? TFT_GREEN : TFT_RED, TFT_BLACK);
        sprite.drawString(xboxConnected ? "Xbox : connectee"
                                        : "Xbox : recherche...", 5, y, 2);
        y += 22;

        sprite.setTextColor(calibrated ? TFT_GREEN : TFT_ORANGE, TFT_BLACK);
        sprite.drawString(calibrated ? "Calibration : OK"
                                     : "Calibration : ...", 5, y, 2);
        y += 22;

        sprite.setTextColor(TFT_CYAN, TFT_BLACK);
        sprite.drawString("Batterie : " + String(xboxBattery) + "%", 5, y, 2);
        y += 22;

        sprite.setTextColor(TFT_WHITE, TFT_BLACK);
        sprite.drawString("G : " + String(leftSpeed) +
                          "   D : " + String(rightSpeed), 5, y, 2);

        sprite.pushSprite(0, 0);
        vTaskDelay(pdMS_TO_TICKS(200));  // 5 Hz
    }
}

// ===== INITIALISATION =====

void setup() {
    Serial.begin(115200);
    Serial2.begin(115200, SERIAL_8N1, RPI_RX, RPI_TX);

    pinMode(PIN_POWER_ON, OUTPUT);
    digitalWrite(PIN_POWER_ON, HIGH);

    tft.init();
    tft.setRotation(1);
    tft.fillScreen(TFT_BLACK);

    sprite.createSprite(320, 170);
    sprite.setSwapBytes(1);

    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.println("Connexion WiFi pour synchronisation NTP...");
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, "pool.ntp.org");
        Serial.println("WiFi connecte, heure synchronisee");
    } else {
        Serial.println("WiFi indisponible, pas de synchronisation d'heure");
    }

    Serial.println("Boutons : A = teleoperation, B = autonome, Y = arret");

    xTaskCreatePinnedToCore(XboxTask,    "XboxTask",    4096, NULL, 1, NULL, 0);
    xTaskCreatePinnedToCore(DisplayTask, "DisplayTask", 4096, NULL, 1, NULL, 1);
}

void loop() {
    vTaskDelay(1);
}
