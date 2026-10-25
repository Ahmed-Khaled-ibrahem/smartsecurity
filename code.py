#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ===================== EDITABLE SETTINGS =====================
const int HARD_THRESHOLD = 600;            // avg >= this -> HARD -> RISK
const int NO_CONTACT_LEVEL = 50;           // readings below this = no contact (ignored in avg)
const byte MIN_CONTACT_PERCENT = 30;       // % of samples that must have contact, else NO CONTACT
const unsigned long SCAN_TIME = 4000;      // loading time (ms)
const unsigned long SAMPLE_INTERVAL = 10;  // FSR read every 10 ms
const unsigned long FRAME_INTERVAL = 60;   // animation frame every 60 ms
const unsigned long DEBOUNCE_MS = 30;

// ===================== PINS =====================
const byte PIN_R = 4;
const byte PIN_G = 3;
const byte PIN_B = 2;
const byte PIN_BTN = 12;
const byte PIN_FSR = A0;

// ===================== OLED =====================
#define SCREEN_W 128
#define SCREEN_H 64
#define OLED_ADDR 0x3C
Adafruit_SSD1306 display(SCREEN_W, SCREEN_H, &Wire, -1);

// ===================== STATE =====================
enum State { IDLE,
             SCANNING,
             RESULT };
enum Result { RES_SAFE,
              RES_RISK,
              RES_NO_CONTACT };

State state = IDLE;
Result result = RES_SAFE;

unsigned long scanStart, lastSample, lastFrame;
unsigned long sum;
unsigned int contactCount, totalCount;
int lastReading = 0;
int avgReading = 0;
byte frame = 0;

// Button debounce
bool lastBtnRead = HIGH;
bool stableBtn = HIGH;
unsigned long lastDebounce = 0;

// Spinner dot positions (8 dots, radius 10)
const int8_t SPX[8] = { 0, 7, 10, 7, 0, -7, -10, -7 };
const int8_t SPY[8] = { -10, -7, 0, 7, 10, 7, 0, -7 };

// ===================== HELPERS =====================
void setLed(bool r, bool g, bool b) {
  digitalWrite(PIN_R, r);
  digitalWrite(PIN_G, g);
  digitalWrite(PIN_B, b);
}

// Returns true once per click (on press edge)
bool buttonClicked() {
  bool reading = digitalRead(PIN_BTN);
  if (reading != lastBtnRead) {
    lastDebounce = millis();
    lastBtnRead = reading;
  }
  if (millis() - lastDebounce > DEBOUNCE_MS && reading != stableBtn) {
    stableBtn = reading;
    if (stableBtn == LOW) return true;
  }
  return false;
}

void printCentered(const __FlashStringHelper* txt, int16_t y, uint8_t size) {
  int16_t x1, y1;
  uint16_t w, h;
  display.setTextSize(size);
  display.getTextBounds(txt, 0, 0, &x1, &y1, &w, &h);
  display.setCursor((SCREEN_W - w) / 2, y);
  display.print(txt);
}

// ===================== SCREENS =====================
void drawIdle() {
  display.clearDisplay();
  printCentered(F("BREAST SCAN"), 2, 1);
  display.drawFastHLine(0, 12, SCREEN_W, SSD1306_WHITE);
  printCentered(F("CLICK"), 20, 2);
  printCentered(F("to start detection"), 42, 1);
  display.display();
}

void drawSpinner(int cx, int cy) {
  byte head = frame % 8;
  for (byte i = 0; i < 8; i++) {
    byte age = (head - i + 8) % 8;  // 0 = leading dot
    int x = cx + SPX[i], y = cy + SPY[i];
    if (age == 0) display.fillCircle(x, y, 3, SSD1306_WHITE);
    else if (age == 1) display.fillCircle(x, y, 2, SSD1306_WHITE);
    else if (age == 2) display.fillCircle(x, y, 1, SSD1306_WHITE);
    else display.drawPixel(x, y, SSD1306_WHITE);
  }
}

void drawScanning(byte percent) {
  display.clearDisplay();

  // Spinner
  drawSpinner(18, 22);

  // "Scanning" + animated dots
  display.setTextSize(1);
  display.setCursor(40, 6);
  display.print(F("Scanning"));
  byte dots = (frame / 4) % 4;
  for (byte i = 0; i < dots; i++) display.print('.');

  // Percentage
  display.setTextSize(2);
  display.setCursor(40, 20);
  display.print(percent);
  display.print('%');

  // Progress bar with moving stripes
  const int bx = 4, by = 42, bw = 120, bh = 10;
  display.drawRoundRect(bx, by, bw, bh, 3, SSD1306_WHITE);
  int fillW = (long)(bw - 4) * percent / 100;
  if (fillW > 0) {
    display.fillRect(bx + 2, by + 2, fillW, bh - 4, SSD1306_WHITE);
    for (int x = bx + 2 + (frame * 2) % 8; x < bx + 2 + fillW; x += 8) {
      display.drawFastVLine(x, by + 2, bh - 4, SSD1306_BLACK);
    }
  }

  // Live reading / hint
  display.setTextSize(1);
  display.setCursor(4, 56);
  if (lastReading < NO_CONTACT_LEVEL) {
    display.print(F("Press on the model"));
  } else {
    display.print(F("Live: "));
    display.print(lastReading);
  }

  display.display();
}

void drawResult() {
  display.clearDisplay();

  if (result == RES_RISK) {
    printCentered(F("RISK"), 2, 3);
    printCentered(F("DETECTED"), 30, 2);
  } else if (result == RES_SAFE) {
    printCentered(F("SAFE"), 6, 3);
    printCentered(F("No risk found"), 36, 1);
  } else {
    printCentered(F("NO"), 2, 2);
    printCentered(F("CONTACT"), 20, 2);
    printCentered(F("Press on the model"), 40, 1);
  }

  // Bottom line: small avg (left) + hint (right)
  display.setTextSize(1);
  if (result != RES_NO_CONTACT) {
    display.setCursor(0, 56);
    display.print(F("Avg: "));
    display.print(avgReading);
  }
  display.setCursor(SCREEN_W - 13 * 6, 56);  // "Click = reset" = 13 chars
  display.print(F("Click = reset"));

  display.display();
}

// ===================== STATE ACTIONS =====================
void goIdle() {
  state = IDLE;
  setLed(0, 0, 0);
  drawIdle();
}

void startScan() {
  state = SCANNING;
  scanStart = millis();
  lastSample = 0;
  lastFrame = 0;
  sum = 0;
  contactCount = 0;
  totalCount = 0;
  frame = 0;
  lastReading = 0;
  setLed(0, 0, 1);  // blue
  drawScanning(0);
  Serial.println(F("--- Scan started ---"));
}

void finishScan() {
  bool enoughContact = totalCount > 0 && (unsigned long)contactCount * 100 >= (unsigned long)totalCount * MIN_CONTACT_PERCENT;

  if (!enoughContact) {
    result = RES_NO_CONTACT;
    avgReading = 0;
    setLed(1, 1, 0);  // yellow
  } else {
    avgReading = sum / contactCount;
    if (avgReading >= HARD_THRESHOLD) {
      result = RES_RISK;
      setLed(1, 0, 0);  // red
    } else {
      result = RES_SAFE;
      setLed(0, 1, 0);  // green
    }
  }

  Serial.print(F("Contact samples: "));
  Serial.print(contactCount);
  Serial.print('/');
  Serial.print(totalCount);
  Serial.print(F("  Avg: "));
  Serial.print(avgReading);
  Serial.print(F("  -> "));
  Serial.println(result == RES_RISK ? F("RISK") : result == RES_SAFE ? F("SAFE")
                                                                     : F("NO CONTACT"));

  state = RESULT;
  drawResult();
}

void updateScan() {
  unsigned long now = millis();
  unsigned long elapsed = now - scanStart;

  // Sample FSR
  if (now - lastSample >= SAMPLE_INTERVAL) {
    lastSample = now;
    int v = analogRead(PIN_FSR);
    lastReading = v;
    totalCount++;
    if (v >= NO_CONTACT_LEVEL) {  // ignore no-contact readings
      sum += v;
      contactCount++;
    }
  }

  if (elapsed >= SCAN_TIME) {
    finishScan();
    return;
  }

  // Animate
  if (now - lastFrame >= FRAME_INTERVAL) {
    lastFrame = now;
    frame++;
    drawScanning(elapsed * 100 / SCAN_TIME);
    Serial.print(F("FSR: "));
    Serial.println(lastReading);
  }
}

// ===================== SETUP / LOOP =====================
void setup() {
  pinMode(PIN_R, OUTPUT);
  pinMode(PIN_G, OUTPUT);
  pinMode(PIN_B, OUTPUT);
  pinMode(PIN_BTN, INPUT);  // external pull-up resistor
  setLed(0, 0, 0);

  Serial.begin(9600);

  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println(F("OLED not found!"));
    while (true) {  // blink red forever if OLED fails
      setLed(1, 0, 0);
      delay(200);
      setLed(0, 0, 0);
      delay(200);
    }
  }
  Wire.setClock(400000);  // faster I2C = smoother animation
  display.setTextColor(SSD1306_WHITE);

  goIdle();
}

void loop() {
  bool clicked = buttonClicked();  // always called to keep debounce state

  switch (state) {
    case IDLE:
      if (clicked) startScan();
      break;
    case SCANNING:
      updateScan();  // clicks ignored
      break;
    case RESULT:
      if (clicked) goIdle();
      break;
  }
}
