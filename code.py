#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ESP32 I2C pins (default)
#define SDA_PIN 21
#define SCL_PIN 22

LiquidCrystal_I2C lcd(0x27, 16, 2);

// Choose ANY GPIO pins
const int ledPin = 18;
const int buzzerPin = 19;

int inhaleTime = 4000;
int holdTime   = 4000;
int exhaleTime = 4000;
const int maxTime = 10000;

void setup() {
  // Initialize I2C for ESP32
  Wire.begin(SDA_PIN, SCL_PIN);

  lcd.init();
  lcd.backlight();

  pinMode(ledPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);

  digitalWrite(ledPin, LOW);
  digitalWrite(buzzerPin, LOW);
}

// Short beep
void bipShort() {
  digitalWrite(buzzerPin, HIGH);
  delay(100);
  digitalWrite(buzzerPin, LOW);
}

// INHALE – display only
void inhalePhase(int duration) {
  int seconds = duration / 1000;
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Inhale...");

  for (int i = seconds; i > 0; i--) {
    lcd.setCursor(0, 1);
    lcd.print("Time: ");
    lcd.print(i);
    lcd.print("s ");
    delay(1000);
  }
}

// HOLD – beep + LED flash every second
void holdPhase(int duration) {
  int seconds = duration / 1000;
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Hold...");

  for (int i = seconds; i > 0; i--) {
    lcd.setCursor(0, 1);
    lcd.print("Time: ");
    lcd.print(i);
    lcd.print("s ");

    bipShort();
    digitalWrite(ledPin, HIGH);
    delay(300);
    digitalWrite(ledPin, LOW);
    delay(700);
  }
}

// EXHALE – display only
void exhalePhase(int duration) {
  int seconds = duration / 1000;
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Exhale...");

  for (int i = seconds; i > 0; i--) {
    lcd.setCursor(0, 1);
    lcd.print("Time: ");
    lcd.print(i);
    lcd.print("s ");
    delay(1000);
  }
}

void loop() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Breathe calmly...");
  delay(2000);

  inhalePhase(inhaleTime);
  holdPhase(holdTime);
  exhalePhase(exhaleTime);

  delay(2000);

  // Increase gradually to 10 seconds
  if (inhaleTime < maxTime) inhaleTime += 1000;
  if (holdTime < maxTime)   holdTime += 1000;
  if (exhaleTime < maxTime) exhaleTime += 1000;
}
