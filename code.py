#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>
#include <SoftwareSerial.h>

#define PIN_RGB_R 3  // RGB Red   (PWM)
#define PIN_RGB_G 5  // RGB Green (PWM)
#define PIN_RGB_B 6  // RGB Blue  (PWM)

#define PIN_BUZZER 8  // Active buzzer

#define PIN_MQ2 A0    // MQ2  smoke / LPG / CO
#define PIN_MQ135 A1  // MQ135 air quality / CO2

#define PIN_FLAME 2                  // Flame sensor (digital, LOW = flame)
#define PIN_FLAME_MODE INPUT_PULLUP  // INPUT or INPUT_PULLUP

#define PIN_DHT 4  // DHT22 data
#define DHT_TYPE DHT11

#define PIN_SIM_RX 10  // SIM800L TX → Arduino pin 10
#define PIN_SIM_TX 11  // SIM800L RX → Arduino pin 11

#define THRESH_MQ2 400         // Raw ADC value (0-1023)
#define THRESH_MQ135 450       // Raw ADC value (0-1023)
#define THRESH_TEMP_HIGH 40.0  // °C
#define THRESH_HUM_HIGH 80.0   // %
#define FLAME_DETECTED HIGH

#define INTERVAL_SENSOR 2000    // How often to read all sensors
#define INTERVAL_SMS 30000      // Min time between SMS alerts
#define INTERVAL_NET_CHECK 10000 // How often to check network registration
#define BUZZER_BEEP_ON 200      // Buzzer ON duration per beep
#define BUZZER_BEEP_OFF 200     // Buzzer OFF between beeps
#define LCD_SCROLL_DELAY 1800   // Time per LCD screen

#define SMS_PHONE_NUMBER "+9665XXXXXXXXX"

LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(PIN_DHT, DHT_TYPE);
SoftwareSerial sim800l(PIN_SIM_RX, PIN_SIM_TX);

float temperature = 0;
float humidity = 0;
int mq2Value = 0;
int mq135Value = 0;
bool flameDetected = false;

bool alertActive = false;
bool netRegistered = false;  // cached network status, refreshed periodically
unsigned long lastSensorRead = 0;
unsigned long lastSMSSent = 0;
unsigned long lastLCDUpdate = 0;
unsigned long lastNetCheck = 0;
int lcdPage = 0;

// ---------------- RGB / LCD / Buzzer (unchanged) ----------------

void setRGB(int r, int g, int b) {
  analogWrite(PIN_RGB_R, r);
  analogWrite(PIN_RGB_G, g);
  analogWrite(PIN_RGB_B, b);
}

void rgbOff() {
  setRGB(0, 0, 0);
}

void rgbGreen() {
  setRGB(0, 255, 0);
}
void rgbRed() {
  setRGB(255, 0, 0);
}
void rgbYellow() {
  setRGB(255, 180, 0);
}
void rgbBlue() {
  setRGB(0, 0, 255);
}
void rgbWhite() {
  setRGB(255, 255, 255);
}

void lcdPrint(String line1, String line2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1.substring(0, 16));
  lcd.setCursor(0, 1);
  lcd.print(line2.substring(0, 16));
}

void lcdAlert(String msg) {
  lcdPrint("!! ALERT !!", msg);
}

void triggerBuzzer(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(PIN_BUZZER, HIGH);
    delay(BUZZER_BEEP_ON);
    digitalWrite(PIN_BUZZER, LOW);
    delay(BUZZER_BEEP_OFF);
  }
}

void buzzerOn() {
  digitalWrite(PIN_BUZZER, HIGH);
}

void buzzerOff() {
  digitalWrite(PIN_BUZZER, LOW);
}

// ---------------- Sensors (unchanged) ----------------

void readAllSensors() {
  temperature = readTemperature();
  humidity = readHumidity();
  mq2Value = readMQ2();
  mq135Value = readMQ135();
  flameDetected = readFlame();
}

float readTemperature() {
  float t = dht.readTemperature();
  if (isnan(t)) {
    Serial.println(F("[DHT] Temperature read failed"));
    return temperature;  // return last valid
  }
  return t;
}

float readHumidity() {
  float h = dht.readHumidity();
  if (isnan(h)) {
    Serial.println(F("[DHT] Humidity read failed"));
    return humidity;
  }
  return h;
}

int readMQ2() {
  return analogRead(PIN_MQ2);
}

int readMQ135() {
  return analogRead(PIN_MQ135);
}

bool readFlame() {
  return (digitalRead(PIN_FLAME) == FLAME_DETECTED);
}

void printSerial() {
  Serial.println(F("-------------------------------"));
  Serial.print(F("Temp:   "));
  Serial.print(temperature);
  Serial.println(F(" C"));
  Serial.print(F("Hum:    "));
  Serial.print(humidity);
  Serial.println(F(" %"));
  Serial.print(F("MQ2:    "));
  Serial.println(mq2Value);
  Serial.print(F("MQ135:  "));
  Serial.println(mq135Value);
  Serial.print(F("Flame:  "));
  Serial.println(flameDetected ? "YES" : "NO");
  Serial.print(F("Alert:  "));
  Serial.println(alertActive ? "YES" : "NO");
  Serial.print(F("Net:    "));
  Serial.println(netRegistered ? "REGISTERED" : "NOT REGISTERED");
}

// ---------------- SIM800L / SMS (rewritten) ----------------

// Reads whatever the module sends for timeoutMs, echoes to Serial,
// and returns everything captured (bounded length to protect RAM).
String simReadResponse(unsigned long timeoutMs, size_t maxLen = 300) {
  String resp;
  unsigned long started = millis();
  while (millis() - started < timeoutMs) {
    while (sim800l.available()) {
      char c = sim800l.read();
      Serial.write(c);
      if (resp.length() < maxLen) resp += c;
    }
  }
  return resp;
}

void simSendAT(const String &cmd, unsigned long waitMs) {
  Serial.print(F(">> "));
  Serial.println(cmd);
  sim800l.println(cmd);
  simReadResponse(waitMs);
  Serial.println();
}

// Checks AT+CPIN? and reports SIM/PIN status clearly.
bool simCheckCard() {
  Serial.println(F(">> AT+CPIN?"));
  sim800l.println(F("AT+CPIN?"));
  String resp = simReadResponse(2000);

  if (resp.indexOf("READY") >= 0) {
    Serial.println(F("[SIM] SIM ready, no PIN needed"));
    return true;
  }
  if (resp.indexOf("SIM PIN") >= 0) {
    Serial.println(F("[SIM] SIM is PIN-locked - unlock it in a phone first"));
  } else if (resp.indexOf("+CME ERROR") >= 0) {
    Serial.println(F("[SIM] CME ERROR - check SIM is inserted correctly"));
  } else {
    Serial.println(F("[SIM] No valid CPIN response - check wiring/power"));
  }
  return false;
}

// Parses the real <stat> digit from AT+CREG? instead of string-matching
// a couple of hardcoded patterns.
bool simCheckNetwork() {
  sim800l.println(F("AT+CREG?"));
  String resp = simReadResponse(2000);

  int idx = resp.indexOf("+CREG:");
  if (idx < 0) return false;

  int comma = resp.indexOf(',', idx);
  int stat = -1;
  if (comma >= 0 && comma + 1 < (int)resp.length()) {
    stat = resp.substring(comma + 1, comma + 2).toInt();
  }
  return (stat == 1 || stat == 5);  // 1 = home, 5 = roaming
}

// Waits specifically for the '>' SMS prompt instead of a fixed delay.
bool simWaitForPrompt(unsigned long timeoutMs = 5000) {
  unsigned long started = millis();
  while (millis() - started < timeoutMs) {
    while (sim800l.available()) {
      char c = sim800l.read();
      Serial.write(c);
      if (c == '>') return true;
    }
  }
  return false;
}

// Sends an SMS and confirms the network actually accepted it (+CMGS:)
// instead of assuming success right after Ctrl+Z.
bool simSendSMS(String number, String message) {
  Serial.println(F("[SIM] Sending SMS..."));

  sim800l.println("AT+CMGS=\"" + number + "\"");
  if (!simWaitForPrompt(5000)) {
    Serial.println(F("[SIM] FAILED - no '>' prompt, message body not sent"));
    return false;
  }

  sim800l.print(message);
  sim800l.write(26);  // Ctrl+Z triggers send

  String resp = simReadResponse(15000);
  if (resp.indexOf("+CMGS:") >= 0) {
    Serial.println(F("[SIM] SMS confirmed sent"));
    return true;
  }
  Serial.println(F("[SIM] FAILED - no +CMGS confirmation from network"));
  return false;
}

// One-time module init: alive check, quiet echo, verbose errors,
// SIM check, text mode, then kick off auto network registration.
void simInit() {
  sim800l.begin(9600);
  delay(3000);

  simSendAT("AT", 1000);
  simSendAT("ATE0", 500);       // echo off
  simSendAT("AT+CMEE=1", 500);  // verbose errors instead of bare "ERROR"

  if (!simCheckCard()) {
    Serial.println(F("[SIM] Fix SIM/PIN issue - SMS will not work until resolved"));
  }

  simSendAT("AT+CMGF=1", 500);   // text mode (set once, not per-SMS)
  simSendAT("AT+COPS=0", 30000); // auto network selection, can take a while
}

// Standalone SIM test loop - set testMessages() in setup() to use this.
void testMessages() {
  Serial.begin(115200);
  simInit();

  while (true) {
    if (simCheckNetwork()) {
      simSendSMS(SMS_PHONE_NUMBER, "Test Message");
    } else {
      Serial.println(F("[SIM] Not registered yet - skipping send"));
    }
    delay(60000);
  }
}

// ---------------- Setup ----------------

void setup() {
  Serial.begin(9600);
  // testRGB();
  // testLCD();
  // testBuzzer();
  // testSensors();
  // testMessages();
  fullSetup();
}

void testRGB() {
  pinMode(PIN_RGB_R, OUTPUT);
  pinMode(PIN_RGB_G, OUTPUT);
  pinMode(PIN_RGB_B, OUTPUT);

  while (1) {
    rgbRed();
    delay(1000);
    rgbGreen();
    delay(1000);
    rgbBlue();
    delay(1000);
  }
}

void testLCD() {
  lcd.init();
  lcd.backlight();
  int counter = 1;
  while (1) {
    lcdPrint("LCD is Working", String(counter));
    delay(1000);
    counter++;
  }
}

void testBuzzer() {
  pinMode(PIN_BUZZER, OUTPUT);

  while (1) {
    triggerBuzzer(3);
    delay(1000);
  }
}

void testSensors() {
  pinMode(PIN_FLAME, PIN_FLAME_MODE);
  dht.begin();
  while (1) {
    readAllSensors();
    printSerial();
    delay(2000);
  }
}

void fullSetup() {
  pinMode(PIN_RGB_R, OUTPUT);
  pinMode(PIN_RGB_G, OUTPUT);
  pinMode(PIN_RGB_B, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_FLAME, PIN_FLAME_MODE);

  lcd.init();
  lcd.backlight();
  lcdPrint("Safety Monitor", "Initializing...");
  delay(1500);

  dht.begin();

  lcdPrint("SIM800L", "Connecting...");
  simInit();
  netRegistered = simCheckNetwork();
  lastNetCheck = millis();

  setRGB(0, 255, 0);
  lcdPrint("System Ready", netRegistered ? "SIM: OK" : "SIM: NO NET");
  delay(1000);

  Serial.println(F("=== Safety Monitor Started ==="));
}

// ---------------- Main loop ----------------

void loop() {
  unsigned long now = millis();

  if (now - lastSensorRead >= INTERVAL_SENSOR) {
    lastSensorRead = now;
    readAllSensors();
    evaluateAlerts(now);
    printSerial();
  }

  // Refresh network status periodically instead of on every alert,
  // so an active fire/gas alarm isn't held up by extra AT+CREG? calls.
  if (now - lastNetCheck >= INTERVAL_NET_CHECK) {
    lastNetCheck = now;
    netRegistered = simCheckNetwork();
  }

  if (now - lastLCDUpdate >= LCD_SCROLL_DELAY) {
    lastLCDUpdate = now;
    updateLCD();
  }
}

void evaluateAlerts(unsigned long now) {
  String alertMsg = "";

  // NOTE: fixed the MQ2 condition below - for MQ2, a HIGHER analog
  // reading means MORE smoke/gas, not less. The original "< THRESH_MQ2"
  // meant an alert only fired when the air was CLEANER than threshold,
  // so SMS alerts for smoke would almost never trigger.
  if (flameDetected) alertMsg += "FLAME! ";
  if (mq2Value > THRESH_MQ2) alertMsg += "SMOKE! ";
  if (mq135Value > THRESH_MQ135) alertMsg += "GAS! ";
  if (temperature > THRESH_TEMP_HIGH) alertMsg += "HIGH TEMP! ";
  if (humidity > THRESH_HUM_HIGH) alertMsg += "HIGH HUM! ";

  if (alertMsg.length() > 0) {
    alertActive = true;
    triggerBuzzer(3);   // 3 beeps
    setRGB(255, 0, 0);  // Red

    if (now - lastSMSSent >= INTERVAL_SMS) {
      if (netRegistered) {
        lastSMSSent = now;
        String sms = "ALERT: " + alertMsg
                     + " T=" + String(temperature, 1) + "C"
                     + " H=" + String(humidity, 1) + "%"
                     + " MQ2=" + String(mq2Value)
                     + " MQ135=" + String(mq135Value);
        simSendSMS(SMS_PHONE_NUMBER, sms);
      } else {
        Serial.println(F("[SIM] Alert active but not registered - SMS skipped"));
      }
    }
  } else {
    alertActive = false;
    buzzerOff();
    setRGB(0, 255, 0);
  }
}

void updateLCD() {
  if (alertActive) {
    String alertLine = "";
    if (flameDetected) alertLine = "FLAME DETECTED";
    else if (mq2Value > THRESH_MQ2) alertLine = "SMOKE/CO HIGH";
    else if (mq135Value > THRESH_MQ135) alertLine = "AIR QUALITY BAD";
    else if (temperature > THRESH_TEMP_HIGH) alertLine = "TEMP TOO HIGH";
    else if (humidity > THRESH_HUM_HIGH) alertLine = "HUMIDITY HIGH";
    lcdAlert(alertLine);
    return;
  }

  switch (lcdPage) {
    case 0:
      lcdPrint("Temp: " + String(temperature, 1) + " C",
               "Hum:  " + String(humidity, 1) + " %");
      break;
    case 1:
      lcdPrint("MQ2:  " + String(mq2Value),
               "MQ135:" + String(mq135Value));
      break;
    case 2:
      lcdPrint("Flame:" + String(flameDetected ? "YES" : "NO"),
               "Status: OK");
      break;
  }

  lcdPage = (lcdPage + 1) % 3;
}
