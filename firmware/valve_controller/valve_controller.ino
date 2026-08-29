/*
 * ============================================================================
 *  Smart Gesture-Controlled Industrial Valve System — Firmware
 * ============================================================================
 *
 *  Listens on the serial port for a single-byte level command (0..10) sent by
 *  the Python HMI (software/gesture_scada.py) and actuates:
 *
 *    1. A servo-driven valve  : level 0..10 -> angle 0..180 deg
 *    2. A 10-LED bargraph     : shows the current level
 *
 *  Protocol (9600 baud, 8N1, 1 byte payload, no framing):
 *    byte value 0..10  = target level
 *
 *  Pin map (Arduino UNO / ATmega328P):
 *    D2..D11 : LED bargraph (10 LEDs, level 1..10)
 *    D12     : Servo signal
 *
 *  Released under the MIT License.
 * ============================================================================
 */

#include <Servo.h>

// ----------------------------- Configuration -------------------------------

const uint8_t  SERVO_PIN        = 12;                        // Valve servo
const uint8_t  LED_COUNT        = 10;                        // Bargraph size
const uint8_t  LED_PINS[LED_COUNT] = {                       // D2..D11
  2, 3, 4, 5, 6, 7, 8, 9, 10, 11
};

const uint8_t  MAX_LEVEL        = 10;                        // Protocol max
const uint8_t  SERVO_MAX_ANGLE  = 180;                       // Valve sweep
const long     BAUD_RATE        = 9600;

// ------------------------------- State -------------------------------------

Servo valve;
int8_t lastLevel = -1;   // Last applied level (-1 = force first update)

// ------------------------------- Setup -------------------------------------

void setup() {
  Serial.begin(BAUD_RATE);

  for (uint8_t i = 0; i < LED_COUNT; i++) {
    pinMode(LED_PINS[i], OUTPUT);
    digitalWrite(LED_PINS[i], LOW);
  }

  valve.attach(SERVO_PIN);
  valve.write(0);        // Start with the valve fully closed
}

// -------------------------------- Loop -------------------------------------

void loop() {
  if (Serial.available() <= 0) {
    return;
  }

  // Read and sanitize one command byte (robust against garbage bytes).
  int level = Serial.read();
  if (level < 0)        level = 0;
  if (level > MAX_LEVEL) level = MAX_LEVEL;

  // Skip redundant updates — saves servo jitter and CPU cycles.
  if (level == lastLevel) {
    return;
  }
  lastLevel = level;

  // 1) Drive the valve: level 0..10  ->  angle 0..180 deg.
  valve.write(map(level, 0, MAX_LEVEL, 0, SERVO_MAX_ANGLE));

  // 2) Update the LED bargraph (LED i lights while i < level).
  for (uint8_t i = 0; i < LED_COUNT; i++) {
    digitalWrite(LED_PINS[i], (i < level) ? HIGH : LOW);
  }
}
