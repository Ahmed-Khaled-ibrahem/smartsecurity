#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>

// ====== LCD ======
LiquidCrystal_I2C lcd(0x27, 16, 2);  // Adjust 0x27 if your LCD has different address

// ====== DHT11 ======
#define DHTPIN 2  // DHT11 data pin
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ====== Pins ======
#define BUZZER_PIN 3
#define RED_PIN 4
#define GREEN_PIN 5
#define BLUE_PIN 6    // not used, but kept if you want blue later
#define SIGNAL_PIN 7  // Digital input 5V signal

// ====== Variables ======
unsigned long lastRead = 0;
const unsigned long readInterval = 2000;  // every 2 seconds

void setup() {
  // Initialize Serial (optional)
  Serial.begin(9600);

  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();

  // DHT sensor
  dht.begin();

  // Pins
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  pinMode(SIGNAL_PIN, INPUT);

  // Start with everything off
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(RED_PIN, LOW);
  digitalWrite(GREEN_PIN, LOW);
  digitalWrite(BLUE_PIN, LOW);

  lcd.setCursor(0, 0);
  lcd.print("System Starting...");
  delay(2000);
  lcd.clear();
}

void loop() {
  int signalState = digitalRead(SIGNAL_PIN);

  if (signalState == HIGH) {
    // ✅ Normal: Electricity ON
    if (millis() - lastRead > readInterval) {
      lastRead = millis();

      float temp = dht.readTemperature();
      float hum = dht.readHumidity();

      lcd.clear();
      if (isnan(temp) || isnan(hum)) {
        lcd.setCursor(0, 0);
        lcd.print("DHT Error!");
      } else {
        lcd.setCursor(0, 0);
        lcd.print("Temp: ");
        lcd.print(temp, 1);
        lcd.print((char)223);  // ° symbol
        lcd.print("C");

        lcd.setCursor(0, 1);
        lcd.print("Hum:  ");
        lcd.print(hum, 1);
        lcd.print("%");
      }

      // Green LED ON
      digitalWrite(GREEN_PIN, HIGH);
      digitalWrite(RED_PIN, LOW);

      // Buzzer OFF
      digitalWrite(BUZZER_PIN, LOW);
    }
  } else {
    // ❌ Electricity DOWN
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("ELECTRICITY");
    lcd.setCursor(0, 1);
    lcd.print("DOWN!");

    // Red LED ON
    digitalWrite(RED_PIN, HIGH);
    digitalWrite(GREEN_PIN, LOW);

    // Buzzer ON
    digitalWrite(BUZZER_PIN, HIGH);

    delay(500);  // Prevent LCD flickering
  }
}
