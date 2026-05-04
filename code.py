#include <Servo.h>
#include <Keypad.h>

#define TEST_MODE true

const int SERVO_PINS[7] = { 2, 3, 4, 5, 6, 7, 8 };
//                          a  b  c  d  e  f  g

// Servo angle when segment is ON  (face visible / arm "closed")
const int SERVO_ON = 90;

// Servo angle when segment is OFF (face hidden  / arm "open")
const int SERVO_OFF = 0;

// Delay between each segment sweep step (ms) — set 0 for instant
const int SEGMENT_SWEEP_DELAY = 60;

const byte ROWS = 4;
const byte COLS = 4;

char KEYPAD_KEYS[ROWS][COLS] = {
  { '1', '2', '3', 'A' },
  { '4', '5', '6', 'B' },
  { '7', '8', '9', 'C' },
  { '*', '0', '#', 'D' }
};

byte ROW_PINS[ROWS] = { 22, 23, 24, 25 };
byte COL_PINS[COLS] = { 26, 27, 28, 29 };

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

// Segment names for Serial output (matches index order a–g)
const char* SEGMENT_NAMES[7] = { "a (top)", "b (top-right)", "c (bottom-right)",
                                 "d (bottom)", "e (bottom-left)", "f (top-left)", "g (middle)" };

const int BLINK_INTERVAL_MS = 400;
const int CHASE_INTERVAL_MS = 150;

// How long each servo stays ON during the test sweep (ms)
const int TEST_ON_DURATION = 1200;

// Pause between testing each servo (ms)
const int TEST_PAUSE = 400;

// How many times to repeat the full sweep at startup
const int TEST_REPEAT_TIMES = 2;

Servo servos[7];
Keypad keypad = Keypad(makeKeymap(KEYPAD_KEYS), ROW_PINS, COL_PINS, ROWS, COLS);

enum Mood { MOOD_NORMAL,
            MOOD_BLINK,
            MOOD_CHASE,
            MOOD_WAVE,
            MOOD_OFF };
Mood currentMood = MOOD_NORMAL;

bool blinkState = false;
int chaseIndex = 0;
unsigned long lastMoodTick = 0;
bool currentPattern[7] = { 0 };

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

void runServoTest() {
  Serial.println(F(""));
  Serial.println(F("========================================"));
  Serial.println(F("  SERVO TEST MODE"));
  Serial.println(F("  Each servo will move one at a time."));
  Serial.println(F("  Watch which arm/segment moves and"));
  Serial.println(F("  note the segment name shown here."));
  Serial.println(F("========================================"));
  Serial.println(F(""));

  for (int rep = 0; rep < TEST_REPEAT_TIMES; rep++) {

    Serial.print(F("--- Sweep #"));
    Serial.print(rep + 1);
    Serial.println(F(" ---"));

    for (int i = 0; i < 7; i++) {
      // All off first so only one servo is clearly moving
      allOff(true);
      delay(TEST_PAUSE);

      Serial.print(F("  >> Moving Servo["));
      Serial.print(i);
      Serial.print(F("] — Segment "));
      Serial.println(SEGMENT_NAMES[i]);
      Serial.print(F("     Pin: "));
      Serial.println(SERVO_PINS[i]);

      // Move this one servo to ON position
      servos[i].write(SERVO_ON);
      delay(TEST_ON_DURATION);

      // Move back to OFF
      servos[i].write(SERVO_OFF);
      delay(TEST_PAUSE);
    }

    Serial.println(F(""));
  }

  // End of test: flash all ON/OFF three times as "done" signal
  Serial.println(F("========================================"));
  Serial.println(F("  TEST COMPLETE — entering normal mode"));
  Serial.println(F("========================================"));

  for (int flash = 0; flash < 3; flash++) {
    allOn();
    delay(300);
    allOff(true);
    delay(300);
  }
}

void handleMoodKey(char key) {
  Serial.print(F("[MOOD] Key: "));
  Serial.println(key);
  currentMood = MOOD_NORMAL;

  switch (key) {

    case 'A':  // Blink current display
      Serial.println(F("[MOOD] Blink ON"));
      currentMood = MOOD_BLINK;
      blinkState = true;
      break;

    case 'B':  // Chasing single segment
      Serial.println(F("[MOOD] Chase ON"));
      allOff(true);
      chaseIndex = 0;
      currentMood = MOOD_CHASE;
      break;

    case 'C':  // Wave animation
      Serial.println(F("[MOOD] Wave ON"));
      currentMood = MOOD_WAVE;
      break;

    case 'D':  // Blank / clear
      Serial.println(F("[MOOD] Clear"));
      allOff();
      currentMood = MOOD_OFF;
      break;

    case '*':  // All segments ON
      Serial.println(F("[MOOD] All ON"));
      allOn();
      break;

    case '#':
      {  // Random digit
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

    case MOOD_BLINK:
      if (now - lastMoodTick >= (unsigned long)BLINK_INTERVAL_MS) {
        lastMoodTick = now;
        blinkState = !blinkState;
        for (int i = 0; i < 7; i++)
          setSegment(i, blinkState ? currentPattern[i] : false);
      }
      break;

    case MOOD_CHASE:
      if (now - lastMoodTick >= (unsigned long)CHASE_INTERVAL_MS) {
        lastMoodTick = now;
        allOff(true);
        setSegment(chaseIndex, true);
        chaseIndex = (chaseIndex + 1) % 7;
      }
      break;

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

  // Attach all servos and park them at OFF position
  for (int i = 0; i < 7; i++) {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(SERVO_OFF);
    Serial.print(F("[SERVO] Attached segment "));
    Serial.print(SEGMENT_NAMES[i]);
    Serial.print(F(" on pin "));
    Serial.println(SERVO_PINS[i]);
  }

  delay(500);  // Let servos settle before test/startup

  randomSeed(analogRead(A0));  // Seed random from floating ADC

  // ----- TEST MODE -----
  if (TEST_MODE) {
    runServoTest();
    // After test, show digit 0 and wait for keypad
  }

  // Startup animation: sweep all ON then show 0
  allOn();
  delay(600);
  showDigit(0);

  Serial.println(F("[BOOT] Ready. Press a key on the keypad."));
}

void loop() {
  char key = keypad.getKey();

  if (key) {
    if (key >= '0' && key <= '9') {
      currentMood = MOOD_NORMAL;
      showDigit(key - '0');
    } else {
      handleMoodKey(key);
    }
  }

  tickMood();
}
