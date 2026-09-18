// ==============================================================================
// KhetRakshak — Complete Deterrent System with Field-Scanning Servo
// 
// Pin Mapping:
//   - Pin 6:  Servo Motor (Camera Scanning)
//   - Pin 7:  Laser Light 1
//   - Pin 8:  Laser Light 2
//   - Pin 9:  Scarecrow Left Eye (Flashlight 1)
//   - Pin 10: Scarecrow Right Eye (Flashlight 2)
// ==============================================================================

#include <Servo.h>

// Pin Definitions
const int SERVO_PIN     = 6;  // PWM Pin for Servo Motor
const int LASER_1_PIN   = 7;  // Relay 3 (Laser 1)
const int LASER_2_PIN   = 8;  // Relay 4 (Laser 2)
const int LEFT_EYE_PIN  = 9;  // Relay 1 (Scarecrow Left Eye)
const int RIGHT_EYE_PIN = 10; // Relay 2 (Scarecrow Right Eye)

// Active-LOW Relay Configuration
const int RELAY_ON  = LOW;
const int RELAY_OFF = HIGH;

// Servo & Scanning Setup
Servo cameraServo;
int servoPos = 90;            // Start at center position (90 degrees)
int servoDirection = 1;       // 1 = sweeping right, -1 = sweeping left
const int SERVO_MIN = 30;     // Leftmost scan boundary
const int SERVO_MAX = 150;    // Rightmost scan boundary
unsigned long lastServoMove = 0;
const int SERVO_SPEED_MS = 25; // Delay between servo steps (controls scan speed)

// State Variables
int patternCounter = 1;       // Tracks eye patterns (1 to 5)

// Helper: Control Flashlight States
void setEyes(bool left, bool right) {
  digitalWrite(LEFT_EYE_PIN, left ? RELAY_ON : RELAY_OFF);
  digitalWrite(RIGHT_EYE_PIN, right ? RELAY_ON : RELAY_OFF);
}

// Helper: Control Laser States
void setLasers(bool active) {
  digitalWrite(LASER_1_PIN, active ? RELAY_ON : RELAY_OFF);
  digitalWrite(LASER_2_PIN, active ? RELAY_ON : RELAY_OFF);
}

// Helper: Turn ALL Relays OFF
void turnAllOff() {
  setEyes(false, false);
  setLasers(false);
}

// Helper: Non-blocking Servo Sweep Function
void scanFieldNonBlocking() {
  unsigned long currentMillis = millis();
  if (currentMillis - lastServoMove >= SERVO_SPEED_MS) {
    lastServoMove = currentMillis;

    servoPos += servoDirection;
    if (servoPos >= SERVO_MAX || servoPos <= SERVO_MIN) {
      servoDirection = -servoDirection; // Reverse direction
    }
    cameraServo.write(servoPos);
  }
}

void setup() {
  // Relay Pins
  pinMode(LEFT_EYE_PIN, OUTPUT);
  pinMode(RIGHT_EYE_PIN, OUTPUT);
  pinMode(LASER_1_PIN, OUTPUT);
  pinMode(LASER_2_PIN, OUTPUT);

  // Default Safe State: All Relays OFF
  turnAllOff();

  // Attach Servo
  cameraServo.attach(SERVO_PIN);
  cameraServo.write(servoPos);

  Serial.begin(9600);
  Serial.println("KhetRakshak System Ready: Relays + Scanning Servo Engaged.");
}

// Check for Emergency Stop mid-sequence
bool checkStopSignal() {
  if (Serial.available() > 0) {
    char cmd = Serial.peek();
    if (cmd == '0') {
      Serial.read(); // Clear character
      turnAllOff();
      Serial.println("Emergency Stop: All Deterrents Deactivated");
      return true;
    }
  }
  return false;
}

// ---------------------------------------------------------------------------
// Eye Lighting Patterns
// ---------------------------------------------------------------------------

// Pattern 1: Alternating Strobe ("Police Flash")
void runPattern1(unsigned long durationMs) {
  Serial.println("Pattern 1: Alternating Strobe");
  unsigned long start = millis();
  while (millis() - start < durationMs) {
    if (checkStopSignal()) return;
    setEyes(true, false); delay(150);
    if (checkStopSignal()) return;
    setEyes(false, true); delay(150);
  }
}

// Pattern 2: Predator Stare & Burst
void runPattern2(unsigned long durationMs) {
  Serial.println("Pattern 2: Predator Stare & Burst");
  unsigned long start = millis();
  while (millis() - start < durationMs) {
    if (checkStopSignal()) return;
    setEyes(true, true); delay(1500);
    for (int i = 0; i < 3; i++) {
      if (checkStopSignal()) return;
      setEyes(true, true); delay(100);
      setEyes(false, false); delay(100);
    }
  }
}

// Pattern 3: Wink & Burst Sequence
void runPattern3(unsigned long durationMs) {
  Serial.println("Pattern 3: Wink & Burst");
  unsigned long start = millis();
  while (millis() - start < durationMs) {
    for (int i = 0; i < 3; i++) {
      if (checkStopSignal()) return;
      setEyes(true, true); delay(150);
      setEyes(true, false); delay(150);
    }
    for (int i = 0; i < 4; i++) {
      if (checkStopSignal()) return;
      setEyes(true, true); delay(80);
      setEyes(false, false); delay(80);
    }
  }
}

// Pattern 4: Random Chaos Flicker
void runPattern4(unsigned long durationMs) {
  Serial.println("Pattern 4: Random Chaos Flicker");
  unsigned long start = millis();
  while (millis() - start < durationMs) {
    if (checkStopSignal()) return;
    setEyes(random(0, 2), random(0, 2));
    delay(random(50, 300));
  }
}

// Pattern 5: Heartbeat Warning Pulse
void runPattern5(unsigned long durationMs) {
  Serial.println("Pattern 5: Heartbeat Warning Pulse");
  unsigned long start = millis();
  while (millis() - start < durationMs) {
    if (checkStopSignal()) return;
    setEyes(true, true); delay(100);
    setEyes(false, false); delay(100);
    setEyes(true, true); delay(100);
    setEyes(false, false); delay(700);
  }
}

// ---------------------------------------------------------------------------
// Main Loop
// ---------------------------------------------------------------------------
void loop() {
  // Standby mode: Camera continuously sweeps to scan the field
  scanFieldNonBlocking();

  if (Serial.available() > 0) {
    char cmd = Serial.read();

    if (cmd == '\n' || cmd == '\r') return; // Ignore whitespace

    if (cmd == '1') {
      Serial.print("MONKEY DETECTED! Triggering Sequence #");
      Serial.println(patternCounter);

      // 1. Activate Lasers
      setLasers(true);

      // 2. Execute active Flashlight Pattern for 10 seconds
      switch (patternCounter) {
        case 1: runPattern1(10000); break;
        case 2: runPattern2(10000); break;
        case 3: runPattern3(10000); break;
        case 4: runPattern4(10000); break;
        case 5: runPattern5(10000); break;
      }

      // 3. Reset deterrent lights and resume camera scanning
      turnAllOff();

      // 4. Increment pattern for next detection (1 -> 2 -> 3 -> 4 -> 5 -> 1)
      patternCounter++;
      if (patternCounter > 5) {
        patternCounter = 1;
      }
    } 
    else if (cmd == '0') {
      turnAllOff();
      Serial.println("CLEAR: System Reset to Standby");
    }
  }
}