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
#define DHT_TYPE DHT22

#define PIN_SIM_RX 10  // SIM800L TX → Arduino pin 10
#define PIN_SIM_TX 11  // SIM800L RX → Arduino pin 11

#define THRESH_MQ2 400         // Raw ADC value (0-1023)
#define THRESH_MQ135 450       // Raw ADC value (0-1023)
#define THRESH_TEMP_HIGH 40.0  // °C
#define THRESH_HUM_HIGH 80.0   // %
#define FLAME_DETECTED LOW

#define INTERVAL_SENSOR 2000   // How often to read all sensors
#define INTERVAL_SMS 30000     // Min time between SMS alerts
#define BUZZER_BEEP_ON 200     // Buzzer ON duration per beep
#define BUZZER_BEEP_OFF 200    // Buzzer OFF between beeps
#define LCD_SCROLL_DELAY 1800  // Time per LCD screen

#define SMS_PHONE_NUMBER "+9665XXXXXXXXX"  // <-- put your number

LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(PIN_DHT, DHT_TYPE);
SoftwareSerial sim800l(PIN_SIM_RX, PIN_SIM_TX);

float temperature = 0;
float humidity = 0;
int mq2Value = 0;
int mq135Value = 0;
bool flameDetected = false;

bool alertActive = false;
unsigned long lastSensorRead = 0;
unsigned long lastSMSSent = 0;
unsigned long lastLCDUpdate = 0;
int lcdPage = 0;

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
}

void simSendAT(String cmd) {
  sim800l.println(cmd);
  delay(500);
  while (sim800l.available()) {
    Serial.write(sim800l.read());
  }
}

void simSendSMS(String number, String message) {
  Serial.println(F("[SIM] Sending SMS..."));
  sim800l.println("AT+CMGF=1");
  delay(300);
  sim800l.println("AT+CMGS=\"" + number + "\"");
  delay(300);
  sim800l.print(message);
  delay(100);
  sim800l.write(26);
  delay(3000);
  Serial.println(F("[SIM] SMS sent"));
}

void setup() {
  Serial.begin(9600);
  testRGB();
  testLCD();
  testBuzzer();
  testSensors();
  testMessages();
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

void testMessages() {
  sim800l.begin(9600);
  delay(1000);
  simSendAT("AT");
  simSendAT("AT+CSQ");
  simSendAT("AT+CCID");
  simSendAT("AT+CREG?");
  simSendAT("AT+CMGF=1");

  while (1) {
    simSendSMS(SMS_PHONE_NUMBER, "Test Message");
    delay(18000);
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

  sim800l.begin(9600);
  delay(1000);
  simSendAT("AT");    
  simSendAT("AT+CMGF=1");  

  setRGB(0, 255, 0);
  lcdPrint("System Ready", "All OK");
  delay(1000);

  Serial.println(F("=== Safety Monitor Started ==="));
}

void loop() {
  unsigned long now = millis();

  if (now - lastSensorRead >= INTERVAL_SENSOR) {
    lastSensorRead = now;
    readAllSensors();
    evaluateAlerts(now);
    printSerial();
  }

  if (now - lastLCDUpdate >= LCD_SCROLL_DELAY) {
    lastLCDUpdate = now;
    updateLCD();
  }
}

void evaluateAlerts(unsigned long now) {
  String alertMsg = "";

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
      lastSMSSent = now;
      String sms = "ALERT: " + alertMsg
                   + " T=" + String(temperature, 1) + "C"
                   + " H=" + String(humidity, 1) + "%"
                   + " MQ2=" + String(mq2Value)
                   + " MQ135=" + String(mq135Value);
      simSendSMS(SMS_PHONE_NUMBER, sms);
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
