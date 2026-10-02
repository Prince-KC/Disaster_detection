/*
 * ==============================================================================
 * विपद्Sathi (BipatSathi) - Disaster Early Warning System
 * LoRa Offline Emergency Alert Receiver & Siren Node (Receiver)
 * ==============================================================================
 * 
 * Functions:
 * 1. Operates completely OFFLINE without Internet, Wi-Fi, or Cellular SIM.
 * 2. Continuously listens for emergency LoRa RF packets at 433 MHz.
 * 3. Receives verified disaster warnings (Landslides, Floods, Fires, Accidents).
 * 4. Measures Signal Strength (RSSI dBm) and Signal-to-Noise Ratio (SNR dB).
 * 5. Automatically triggers physical community alarm:
 *    - Sounds emergency buzzer / siren pattern
 *    - Flashes high-visibility emergency strobe LED
 * 6. Outputs structured disaster alert reports to Serial console / field displays.
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
// Must match the Sender frequency: 433E6 (433 MHz)
#define LORA_BAND 433E6

// ------------------------------------------------------------------------------
// Pin Configuration (Select appropriate preset for your board)
// ------------------------------------------------------------------------------
// Preset A: ESP8266 / NodeMCU (Default)
#define LORA_SS       15  // D8 on NodeMCU
#define LORA_RST      16  // D0 on NodeMCU
#define LORA_DIO0     2   // D4 on NodeMCU
#define BUZZER_PIN    4   // D2 on NodeMCU (Piezo Buzzer / Relay for Siren)
#define ALARM_LED_PIN 5   // D1 on NodeMCU (Warning Strobe LED)

// Preset B: ESP32 (Uncomment if using standard ESP32 Dev Board)
// #define LORA_SS       5
// #define LORA_RST      14
// #define LORA_DIO0     2
// #define BUZZER_PIN    12
// #define ALARM_LED_PIN 13

// Preset C: Arduino Uno / Nano (Uncomment if using Arduino Uno/Nano)
// #define LORA_SS       10
// #define LORA_RST      9
// #define LORA_DIO0     2
// #define BUZZER_PIN    6
// #define ALARM_LED_PIN 7

// ------------------------------------------------------------------------------
// Alarm Timing & State
// ------------------------------------------------------------------------------
bool alarmActive = false;
unsigned long alarmStartTime = 0;
const unsigned long ALARM_DURATION_MS = 6000; // Siren sounds for 6 seconds on alert
unsigned long totalAlertsReceived = 0;

// ------------------------------------------------------------------------------
// Helper: Sound Emergency Siren Pattern (Non-blocking or rapid pulse)
// ------------------------------------------------------------------------------
void triggerEmergencyAlarm() {
  alarmActive = true;
  alarmStartTime = millis();

  // Rapid alarm strobe and sound alert
  for (int cycle = 0; cycle < 3; cycle++) {
    digitalWrite(ALARM_LED_PIN, HIGH);
    tone(BUZZER_PIN, 1800, 150); // High pitch warning
    delay(150);
    digitalWrite(ALARM_LED_PIN, LOW);
    tone(BUZZER_PIN, 1200, 150); // Low pitch warning
    delay(150);
  }
}

// ------------------------------------------------------------------------------
// Helper: Update Siren State in Loop
// ------------------------------------------------------------------------------
void updateAlarmState() {
  if (alarmActive) {
    if (millis() - alarmStartTime > ALARM_DURATION_MS) {
      alarmActive = false;
      noTone(BUZZER_PIN);
      digitalWrite(ALARM_LED_PIN, LOW);
      Serial.println(F("[Siren Node] Alarm auto-silenced. Standby."));
    } else {
      // Pulse LED while alarm is active
      int blinkState = (millis() / 200) % 2;
      digitalWrite(ALARM_LED_PIN, blinkState ? HIGH : LOW);
    }
  }
}

// ------------------------------------------------------------------------------
// Setup
// ------------------------------------------------------------------------------
void setup() {
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(ALARM_LED_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(ALARM_LED_PIN, LOW);

  Serial.begin(9600);
  delay(1000);

  Serial.println();
  Serial.println(F("=================================================="));
  Serial.println(F(" विपद्Sathi (BipatSathi) - OFFLINE EMERGENCY NODE"));
  Serial.println(F(" LoRa Disaster Alert Receiver & Siren Controller"));
  Serial.println(F("=================================================="));

  // Configure SPI pins for LoRa module
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  Serial.print(F("[LoRa] Initializing radio at 433 MHz... "));
  if (!LoRa.begin(LORA_BAND)) {
    Serial.println(F("FAILED!"));
    Serial.println(F("[LoRa] Check wiring (SS, RST, DIO0, SCK, MISO, MOSI). Halting."));
    while (1) {
      digitalWrite(ALARM_LED_PIN, HIGH);
      delay(200);
      digitalWrite(ALARM_LED_PIN, LOW);
      delay(200);
    }
  }

  // Matching configuration for long-range emergency reception
  LoRa.setSpreadingFactor(10);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);

  Serial.println(F("SUCCESS."));
  Serial.println(F("[LORA_RECEIVER_READY] Listening for offline disaster broadcasts..."));

  // Short startup chirp
  tone(BUZZER_PIN, 2000, 100);
  digitalWrite(ALARM_LED_PIN, HIGH);
  delay(100);
  digitalWrite(ALARM_LED_PIN, LOW);
}

// ------------------------------------------------------------------------------
// Main Loop
// ------------------------------------------------------------------------------
void loop() {
  updateAlarmState();

  // Check for incoming LoRa RF packet
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    totalAlertsReceived++;

    String incomingData = "";
    while (LoRa.available()) {
      incomingData += (char)LoRa.read();
    }
    incomingData.trim();

    // Signal telemetry
    int rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();

    // Determine signal quality indicator
    String signalQuality = "Fair";
    if (rssi > -75) signalQuality = "Strong";
    else if (rssi < -100) signalQuality = "Weak";

    // Print rich disaster alert banner to field monitor
    Serial.println();
    Serial.println(F("************************************************************"));
    Serial.println(F("🚨🚨🚨 [विपद्Sathi] OFFLINE DISASTER ALERT RECEIVED! 🚨🚨🚨"));
    Serial.println(F("************************************************************"));
    Serial.print(F("ALERT PAYLOAD : "));
    Serial.println(incomingData);
    Serial.print(F("ALERT NUMBER  : #"));
    Serial.println(totalAlertsReceived);
    Serial.print(F("SIGNAL (RSSI) : "));
    Serial.print(rssi);
    Serial.print(F(" dBm ("));
    Serial.print(signalQuality);
    Serial.println(F(")"));
    Serial.print(F("SIGNAL SNR    : "));
    Serial.print(snr);
    Serial.println(F(" dB"));
    Serial.print(F("PACKET SIZE   : "));
    Serial.print(packetSize);
    Serial.println(F(" bytes"));
    Serial.println(F("ACTION        : ACTIVATING OFFLINE COMMUNITY SIREN & STROBE"));
    Serial.println(F("************************************************************"));
    Serial.println();

    // Sound siren & flash strobe
    triggerEmergencyAlarm();
  }

  // Also support manual Serial test commands from local USB monitor if connected
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.equalsIgnoreCase("TEST_SIREN")) {
      Serial.println(F("[Receiver] Manual siren test triggered."));
      triggerEmergencyAlarm();
    } else if (cmd.equalsIgnoreCase("STATUS")) {
      Serial.print(F("[Receiver Status] Alerts received: "));
      Serial.println(totalAlertsReceived);
    }
  }

  yield(); // Keep background processing active
}
