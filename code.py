#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

/*
PINOUT:
RC522 MODULE    Uno/Nano     MEGA
SDA             D10          D9
SCK             D13          D52
MOSI            D11          D51
MISO            D12          D50
IRQ             N/A          N/A
GND             GND          GND
RST             D9           D8
3.3V            3.3V         3.3V
*/

#define SS_PIN 53
#define RST_PIN 5

#define RED_PIN 6
#define GREEN_PIN 7
#define BLUE_PIN 8

#define SIM800 Serial1

// ================= OBJECTS =================
MFRC522 rfid(SS_PIN, RST_PIN);
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ================= INIT FUNCTIONS =================
void initLCD() {
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("LCD Ready");
}

void initRFID() {
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("RFID Ready");
}

void initSIM800() {
  SIM800.begin(9600);
  delay(1000);
  Serial.println("SIM800 Ready");
}

void initRGB() {
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
}

// ================= LCD FUNCTIONS =================
void lcdPrint(String line1, String line2 = "") {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1);
  lcd.setCursor(0, 1);
  lcd.print(line2);
}

// ================= RGB FUNCTIONS =================
void setRGB(int r, int g, int b) {
  analogWrite(RED_PIN, r);
  analogWrite(GREEN_PIN, g);
  analogWrite(BLUE_PIN, b);
}

// ================= RFID FUNCTIONS =================
String readRFID() {
  if (!rfid.PICC_IsNewCardPresent()) return "";
  if (!rfid.PICC_ReadCardSerial()) return "";

  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uid += String(rfid.uid.uidByte[i], HEX);
  }

  uid.toUpperCase();
  rfid.PICC_HaltA();
  return uid;
}

// ================= SIM800 FUNCTIONS =================
void sendAT(String cmd) {
  SIM800.println(cmd);
  delay(500);
  while (SIM800.available()) {
    Serial.write(SIM800.read());
  }
}

void sendSMS(String number, String message) {
  sendAT("AT+CMGF=1");  // text mode
  delay(500);

  SIM800.print("AT+CMGS=\"");
  SIM800.print(number);
  SIM800.println("\"");
  delay(500);

  SIM800.print(message);
  delay(500);

  SIM800.write(26);  // CTRL+Z
  delay(3000);
}

// ================= TEST FUNCTIONS =================
void testLCD() {
  lcdPrint("Testing LCD", "Working...");
  delay(2000);
}

void testRGB() {
  setRGB(255, 0, 0);
  delay(500);
  setRGB(0, 255, 0);
  delay(500);
  setRGB(0, 0, 255);
  delay(500);
  setRGB(255, 255, 255);
  delay(500);
  setRGB(0, 0, 0);
}

void testSIM800() {
  sendAT("AT");
  sendAT("AT+CSQ");  // signal quality
}

void testRFID() {
  lcdPrint("Scan Card...");
  while (true) {
    String id = readRFID();
    if (id != "") {
      Serial.println("Card UID: " + id);
      lcdPrint("Card Detected", id);
      setRGB(0, 255, 0);
      delay(2000);
      break;
    }
  }
}

// ================= SETUP =================
void setup() {
  Serial.begin(9600);

  initLCD();
  initRGB();
  initRFID();
  initSIM800();

  // testLCD();
  // testRGB();
  // testSIM800();
}

void code() {
  // RFID continuous read
  String cardID = readRFID();

  if (cardID != "") {
    Serial.println("UID: " + cardID);

    lcdPrint("Access Card:", cardID);

    setRGB(0, 255, 0);

    // Example: send SMS when scanned
    sendSMS("+201XXXXXXXXX", "Card Detected: " + cardID);

    delay(3000);
    setRGB(0, 0, 0);
  }
}

// ================= LOOP =================
void loop() {
  code();
  delay(20);
}
