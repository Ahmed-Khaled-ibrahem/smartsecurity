#include <Servo.h>
#include <Keypad.h>

const int SERVO_PINS[7] = { 2, 3, 4, 5, 6, 7, 8 };
//                           a  b  c  d  e  f  g

const int SERVO_ON = 0;    // Servo angle when segment is ON
const int SERVO_OFF = 90;  // Servo angle when segment is OFF

const int SEGMENT_SWEEP_DELAY = 60;

const int COUNT_STEP_MS = 800;

const byte ROWS = 4;
const byte COLS = 4;

char KEYPAD_KEYS[ROWS][COLS] = {
  { '1', '2', '3', 'A' },
  { '4', '5', '6', 'B' },
  { '7', '8', '9', 'C' },
  { '*', '0', '#', 'D' }
};

byte ROW_PINS[ROWS] = { 26, 27, 28, 29 };
byte COL_PINS[COLS] = { 22, 23, 24, 25 };

const bool DIGITS[10][7] = {
  //   a  b  c  d  e  f  g
  { 1, 1, 1, 1, 1, 1, 0 },  // 0
  { 0, 1, 1, 0, 0, 0, 0 },  // 1
  { 1, 1, 0, 1, 1, 0, 1 },  // 2
  { 1, 1, 1, 1, 0, 0, 1 },  // 3
  { 0, 1, 1, 0, 0, 1, 1 },  // 4
  { 1, 0, 1, 1, 0, 1, 1 },  // 5
  { 1, 0, 1, 1, 1, 1, 1 },  // 6
  { 1, 1, 1, 0, 0, 0, 0 },  // 7
  { 1, 1, 1, 1, 1, 1, 1 },  // 8
  { 1, 1, 1, 1, 0, 1, 1 },  // 9
};

const char* SEGMENT_NAMES[7] = {
  "a (top)", "b (top-right)", "c (bottom-right)",
  "d (bottom)", "e (bottom-left)", "f (top-left)", "g (middle)"
};

const int BLINK_INTERVAL_MS = 400;
const int CHASE_INTERVAL_MS = 150;

Servo servos[7];
Keypad keypad = Keypad(makeKeymap(KEYPAD_KEYS), ROW_PINS, COL_PINS, ROWS, COLS);

enum Mood {
  MOOD_NORMAL,
  MOOD_COUNT_UP,
  MOOD_COUNT_DOWN,
  MOOD_WAVE,
  MOOD_OFF
};
Mood currentMood = MOOD_NORMAL;

bool blinkState = false;
int chaseIndex = 0;
unsigned long lastMoodTick = 0;
bool currentPattern[7] = { 0 };

int countCurrent = 0;       // digit currently on display during count
bool countRunning = false;  // is the counter actively ticking?

void setSegment(int seg, bool on) {
  servos[seg].write(on ? SERVO_ON : SERVO_OFF);
}

void showPattern(const bool pattern[7], bool animated = true) {
  for (int i = 0; i < 7; i++) {
    currentPattern[i] = pattern[i];
    setSegment(i, pattern[i]);
    if (animated && SEGMENT_SWEEP_DELAY > 0) delay(SEGMENT_SWEEP_DELAY);
  }
}

void showDigit(int d, bool animated = true) {
  if (d < 0 || d > 9) return;
  Serial.print(F("[DISPLAY] Digit: "));
  Serial.println(d);
  showPattern(DIGITS[d], animated);
}

void allOff(bool silent = false) {
  for (int i = 0; i < 7; i++) {
    currentPattern[i] = false;
    setSegment(i, false);
  }
  if (!silent) Serial.println(F("[DISPLAY] All OFF"));
}

void allOn() {
  for (int i = 0; i < 7; i++) {
    currentPattern[i] = true;
    setSegment(i, true);
  }
  Serial.println(F("[DISPLAY] All ON"));
}

void handleKey(char key) {
  Serial.print(F("[KEY] Pressed: "));
  Serial.println(key);

  // --- Digit keys ---
  if (key >= '0' && key <= '9') {
    currentMood = MOOD_NORMAL;
    countRunning = false;
    showDigit(key - '0');
    return;
  }

  switch (key) {

    case 'A':  
      if (currentMood == MOOD_COUNT_UP) {
        countRunning = !countRunning;
        Serial.println(countRunning ? F("[COUNT] Resumed UP") : F("[COUNT] Paused"));
      } else {
        currentMood = MOOD_COUNT_UP;
        countCurrent = 1;
        countRunning = true;
        lastMoodTick = millis() - COUNT_STEP_MS; 
        Serial.println(F("[COUNT] Start UP 1→9"));
      }
      break;

    case 'B': 
      if (currentMood == MOOD_COUNT_DOWN) {
        countRunning = !countRunning;
        Serial.println(countRunning ? F("[COUNT] Resumed DOWN") : F("[COUNT] Paused"));
      } else {
        currentMood = MOOD_COUNT_DOWN;
        countCurrent = 9;
        countRunning = true;
        lastMoodTick = millis() - COUNT_STEP_MS;  // show first digit immediately
        Serial.println(F("[COUNT] Start DOWN 9→1"));
      }
      break;

    case 'C':  // Wave animation
      Serial.println(F("[MOOD] Wave ON"));
      currentMood = MOOD_WAVE;
      countRunning = false;
      break;

    case 'D':  // Blank / clear
      Serial.println(F("[MOOD] Clear"));
      currentMood = MOOD_OFF;
      countRunning = false;
      allOff();
      break;

    case '*':  // All segments ON
      Serial.println(F("[MOOD] All ON"));
      currentMood = MOOD_NORMAL;
      countRunning = false;
      allOn();
      break;

    case '#':  // Random digit
      {
        currentMood = MOOD_NORMAL;
        countRunning = false;
        int r = random(0, 10);
        Serial.print(F("[MOOD] Random digit: "));
        Serial.println(r);
        showDigit(r);
        break;
      }
  }
}

void tickMood() {
  unsigned long now = millis();

  switch (currentMood) {

    // ------ Count UP 1 → 9 ------
    case MOOD_COUNT_UP:
      if (!countRunning) break;
      if (now - lastMoodTick >= (unsigned long)COUNT_STEP_MS) {
        lastMoodTick = now;
        showDigit(countCurrent, false);  // no sweep delay during auto-count
        if (countCurrent < 9) {
          countCurrent++;
        } else {
          // Reached 9 — stop automatically
          countRunning = false;
          Serial.println(F("[COUNT] Reached 9, stopped"));
        }
      }
      break;

    // ------ Count DOWN 9 → 1 ------
    case MOOD_COUNT_DOWN:
      if (!countRunning) break;
      if (now - lastMoodTick >= (unsigned long)COUNT_STEP_MS) {
        lastMoodTick = now;
        showDigit(countCurrent, false);
        if (countCurrent > 1) {
          countCurrent--;
        } else {
          // Reached 1 — stop automatically
          countRunning = false;
          Serial.println(F("[COUNT] Reached 1, stopped"));
        }
      }
      break;

    // ------ Wave ------
    case MOOD_WAVE:
      {
        static int waveStep = 0;
        static bool waveDir = true;
        if (now - lastMoodTick >= (unsigned long)CHASE_INTERVAL_MS) {
          lastMoodTick = now;
          allOff(true);
          if (waveDir) {
            for (int i = 0; i <= waveStep; i++) setSegment(i, true);
            waveStep++;
            if (waveStep >= 7) {
              waveDir = false;
              waveStep = 6;
            }
          } else {
            for (int i = 0; i <= waveStep; i++) setSegment(i, true);
            waveStep--;
            if (waveStep < 0) {
              waveDir = true;
              waveStep = 0;
            }
          }
        }
        break;
      }

    default:
      break;
  }
}

void setup() {
  Serial.begin(9600);
  Serial.println(F("[BOOT] Servo 7-Segment Display — Arduino Mega"));

  for (int i = 0; i < 7; i++) {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(SERVO_OFF);
    Serial.print(F("[SERVO] Attached segment "));
    Serial.print(SEGMENT_NAMES[i]);
    Serial.print(F(" on pin "));
    Serial.println(SERVO_PINS[i]);
  }

  delay(500);
  randomSeed(analogRead(A0));

  // Startup animation: flash all ON then show 0
  allOn();
  delay(600);
  showDigit(0);

  Serial.println(F("[BOOT] Ready. Press a key on the keypad."));
}

void loop() {
  char key = keypad.getKey();
  if (key) handleKey(key);
  tickMood();
}
