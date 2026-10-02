/*
 * ==============================================================================
 * विपद्Sathi (BipatSathi) - Disaster Early Warning System
 * LoRa Offline Emergency Alert Transmitter Gateway (Sender)
 * ==============================================================================
 * 
 * Functions:
 * 1. Connects to Python Backend / Edge Detection PC via USB Serial (9600 baud).
 * 2. Receives confirmed disaster alerts (Landslides, Floods, Fires, Accidents).
 * 3. Broadcasts high-priority emergency packets over LoRa RF (433 MHz).
 * 4. Transmits to offline field stations, siren posts, and remote communities
 *    without requiring cellular network, Wi-Fi, or internet connection.
 * 
 * Supported Hardware:
 * - ESP8266 (NodeMCU / Wemos D1 Mini) [Default Pinout]
 * - ESP32 / TTGO LoRa32
 * - Arduino Uno / Nano with SX1278 (Ra-02) / SX1276 module
 * ==============================================================================
 */

#include <SPI.h>
#include <LoRa.h>

// ------------------------------------------------------------------------------
// Radio Frequency Configuration
// ------------------------------------------------------------------------------
// Nepal / Asia / Europe ISM Band standard: 433E6 (433 MHz)
// Alternatives: 868E6 (868 MHz) or 915E6 (915 MHz)
#define LORA_BAND 433E6

// ------------------------------------------------------------------------------
// Pin Configuration (Select appropriate preset for your board)
// ------------------------------------------------------------------------------
// Preset A: ESP8266 / NodeMCU (Default)
#define LORA_SS    15  // D8 on NodeMCU
#define LORA_RST   16  // D0 on NodeMCU
#define LORA_DIO0  2   // D4 on NodeMCU
#define LED_TX     2   // Built-in LED on NodeMCU (active LOW)

// Preset B: ESP32 (Uncomment if using standard ESP32 Dev Board)
// #define LORA_SS    5
// #define LORA_RST   14
// #define LORA_DIO0  2
// #define LED_TX     2

// Preset C: Arduino Uno / Nano (Uncomment if using Arduino Uno/Nano)
// #define LORA_SS    10
// #define LORA_RST   9
// #define LORA_DIO0  2
// #define LED_TX     13

// ------------------------------------------------------------------------------
// Global State Variables
// ------------------------------------------------------------------------------
unsigned long lastHeartbeat = 0;
const unsigned long HEARTBEAT_INTERVAL = 60000; // 60s radio alive beacon
unsigned long packetCount = 0;
String serialBuffer = "";

// ------------------------------------------------------------------------------
// Helper: Flash TX LED
// ------------------------------------------------------------------------------
void flashTxLed(int times = 1, int durationMs = 80) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_TX, LOW);  // Turn on LED (active low on ESP8266)
    delay(durationMs);
    digitalWrite(LED_TX, HIGH); // Turn off LED
    if (i < times - 1) delay(60);
  }
}

// ------------------------------------------------------------------------------
// Helper: Transmit LoRa Disaster Alert Packet
// ------------------------------------------------------------------------------
bool broadcastLoRaAlert(String alertPayload) {
  alertPayload.trim();
  if (alertPayload.length() == 0) return false;

  flashTxLed(2, 60);

  Serial.print(F("[LoRa TX] Broadcasting packet #"));
  Serial.print(++packetCount);
  Serial.print(F(": "));
  Serial.println(alertPayload);

  // Transmit over LoRa RF
  LoRa.beginPacket();
  LoRa.print(alertPayload);
  int txResult = LoRa.endPacket(); // returns 1 on success

  if (txResult == 1) {
    Serial.println(F("[LORA_TX_SUCCESS]"));
    return true;
  } else {
    Serial.println(F("[LORA_TX_ERROR] Failed to send radio packet"));
    return false;
  }
}

// ------------------------------------------------------------------------------
// Setup
// ------------------------------------------------------------------------------
void setup() {
  pinMode(LED_TX, OUTPUT);
  digitalWrite(LED_TX, HIGH); // Off initially

  Serial.begin(9600);
  delay(1000);

  Serial.println();
  Serial.println(F("=================================================="));
  Serial.println(F(" विपद्Sathi (BipatSathi) - Offline LoRa Alert"));
  Serial.println(F(" Emergency Radio Transmitter Node (Sender)"));
  Serial.println(F("=================================================="));

  // Configure SPI pins for LoRa module
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  Serial.print(F("[LoRa] Initializing radio at 433 MHz... "));
  if (!LoRa.begin(LORA_BAND)) {
    Serial.println(F("FAILED!"));
    Serial.println(F("[LoRa] Check wiring (SS, RST, DIO0, SCK, MISO, MOSI). Halting."));
    while (1) {
      flashTxLed(1, 300);
      delay(300);
    }
  }

  // Optimize LoRa transmission settings for long-range emergency penetration
  LoRa.setTxPower(20);          // Maximum transmission power (20 dBm = 100mW)
  LoRa.setSpreadingFactor(10);   // Spreading Factor 10 for extended rural range
  LoRa.setSignalBandwidth(125E3);// 125 kHz bandwidth
  LoRa.setCodingRate4(5);        // 4/5 error correction rate

  Serial.println(F("SUCCESS."));
  Serial.println(F("[LORA_SENDER_READY] Transmitter online. Awaiting backend alerts..."));

  // Send boot notification beacon
  broadcastLoRaAlert(F("[विपद्Sathi-LORA] GATEWAY_ONLINE: 433MHz Emergency Grid Ready"));
}

// ------------------------------------------------------------------------------
// Main Loop
// ------------------------------------------------------------------------------
void loop() {
  // 1. Process incoming commands from Python Backend over Serial
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') continue;

    if (c == '\n') {
      serialBuffer.trim();
      if (serialBuffer.length() > 0) {
        // Handle command protocols
        if (serialBuffer.equalsIgnoreCase("PING")) {
          Serial.println(F("[LORA_PONG] Transmitter responsive"));
        } else if (serialBuffer.equalsIgnoreCase("STATUS")) {
          Serial.print(F("[LORA_STATUS] Packets Sent: "));
          Serial.println(packetCount);
        } else if (serialBuffer.equalsIgnoreCase("TEST")) {
          broadcastLoRaAlert(F("[विपद्Sathi-LORA] ⚠️ SYSTEM TEST: Disaster Radio Link Verified"));
        } else {
          // Treat any other serial message as an emergency alert to broadcast
          broadcastLoRaAlert(serialBuffer);
        }
      }
      serialBuffer = "";
    } else {
      serialBuffer += c;
      if (serialBuffer.length() > 240) {
        // Prevent buffer overflow
        serialBuffer = "";
      }
    }
  }

  // 2. Periodic radio standby beacon (every 60 seconds)
  unsigned long now = millis();
  if (now - lastHeartbeat >= HEARTBEAT_INTERVAL) {
    lastHeartbeat = now;
    // Keep local serial terminal updated
    Serial.println(F("[LoRa Standby] Awaiting alert commands..."));
  }

  yield(); // Keep ESP8266 background tasks fed
}
