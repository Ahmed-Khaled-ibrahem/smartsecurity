#include <WiFi.h>
#include <Firebase_ESP_Client.h>
#include <addons/TokenHelper.h>
#include <addons/RTDBHelper.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <BLEDevice.h>
#include <BLEAdvertising.h>
#include <time.h>

// WiFi
#define WIFI_SSID "Orange-Fast"
#define WIFI_PASSWORD "#1288534459&4274321#Aa"

// Firebase RTDB
#define FIREBASE_HOST "https://mawqifi-81e4b-default-rtdb.firebaseio.com"
#define FIREBASE_API_KEY "AIzaSyDOWRS5hc5XN-5sTb3oBuCyiuV5jQeurjw"

// Firebase Auth — email/password account for all ESP units
#define FIREBASE_USER_EMAIL "esp@gmail.com"
#define FIREBASE_USER_PASS "12345678"

// Pin definitions
#define TRIG_PIN 25
#define ECHO_PIN 26
#define LED_RED_PIN 5
#define LED_GREEN_PIN 18
#define LED_BLUE_PIN 19
#define BUZZER_PIN 23

// LCD I2C (address is usually 0x27 or 0x3F — check your module)
#define LCD_I2C_ADDR 0x27
#define LCD_COLS 16
#define LCD_ROWS 2

// Sensor settings
#define CAR_DISTANCE_CM 20  // distance (cm) at or below = car present

// ─── Firebase objects ─────────────────────────
FirebaseData fbStream;    // dedicated object for the label stream
FirebaseData bookStream;  // dedicated object for the label stream
FirebaseData fbWrite;     // used only for writes
FirebaseAuth auth;
FirebaseConfig config;

// ─── Globals ──────────────────────────────────
LiquidCrystal_I2C lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS);

String unitId = "";  // set at runtime from MAC address
bool carPresent = false;
bool lastCarPresent = false;
String currentLabel = "...";
String currentStatus = "";

time_t bookedTime;
bool timerFinished = true;

String userId = "";

// ─── Path helpers ─────────────────────────────
String unitPath() {
  return "/units/" + unitId;
}
String statusPath() {
  return unitPath() + "/status";
}
String labelPath() {
  return unitPath() + "/label";
}
String bookPath() {
  return unitPath() + "/bookedAt";
}
String userIdPath() {
  return unitPath() + "/bookedBy";
}

// Forward declarations
void lcdShow(String line1, String line2);
void updateLED(bool busy);
void beepStatusChange();

void onLabelStream(FirebaseStream data) {
  Serial.println("[STREAM] Event received");
  Serial.println("[STREAM] Path  : " + data.streamPath());
  Serial.println("[STREAM] Event : " + data.eventType());
  Serial.println("[STREAM] Type  : " + data.dataType());

  if (data.dataTypeEnum() == fb_esp_rtdb_data_type_string) {
    String newLabel = data.stringData();
    Serial.println("[STREAM] New label value → " + newLabel);

    if (newLabel != currentLabel) {
      currentLabel = newLabel;
      lcdShow(currentLabel, currentStatus + userId);
    } else {
      Serial.println("[STREAM] Label unchanged, skipping LCD update");
    }
  }
}

void onBookedStream(FirebaseStream data) {
  Serial.println("[STREAM] Event received");
  Serial.println("[STREAM] Path  : " + data.streamPath());
  Serial.println("[STREAM] Event : " + data.eventType());
  Serial.println("[STREAM] Type  : " + data.dataType());

  if (data.dataTypeEnum() == fb_esp_rtdb_data_type_string) {
    String bookedAt = data.stringData();
    Serial.println("[STREAM] New booking value → " + bookedAt);
    bookedTime = parseFirebaseTime(bookedAt);
    timerFinished = false;
    userId = " - " + readUserId(fbWrite, userIdPath());
    lcdShow(currentLabel, "booked" + userId);
    Serial.println("Result: " + userId);
  }
}

// Stream timeout callback — library auto-reconnects after this
void onStreamTimeout(bool timeout) {
  if (timeout) {
    Serial.println("[STREAM] Timed out — reconnecting...");
  }
}

void ble_setup(String name) {
  BLEDevice::init(name.c_str());

  BLEAdvertising *advertising = BLEDevice::getAdvertising();
  advertising->setScanResponse(true);

  BLEDevice::startAdvertising();

  Serial.println("[BLE] Advertising as: " + name);
}

void initTime() {
  configTime(0, 0, "time.google.com", "pool.ntp.org");

  Serial.print("Waiting for time");
  time_t now = time(nullptr);

  while (now < 100000) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
  }

  Serial.println("\nTime initialized");
}
// ══════════════════════════════════════════════
//  SETUP
// ══════════════════════════════════════════════
void setup() {
  Serial.begin(9600);

  unitId = WiFi.macAddress();  // format: "A4:CF:12:34:56:78"
  Serial.println("\n[BOOT] Unit ID (MAC): " + unitId);
  ble_setup(unitId);
  // ── Pin modes ──
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_BLUE_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_BLUE_PIN, LOW);  // blue stays off always

  // ── LCD init ──
  lcd.init();
  lcd.backlight();
  lcdShow("Booting...", "");

  // ── WiFi ──
  connectWiFi();
  initTime();

  // ── Firebase config — email/password auth ──
  config.database_url = FIREBASE_HOST;
  config.api_key = FIREBASE_API_KEY;
  config.token_status_callback = tokenStatusCallback;
  auth.user.email = FIREBASE_USER_EMAIL;
  auth.user.password = FIREBASE_USER_PASS;

  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  Serial.print("[FIREBASE] Signing in as " + String(FIREBASE_USER_EMAIL));
  lcdShow("Firebase...", "Signing in...");
  while (!Firebase.ready()) {
    Serial.print(".");
    delay(300);
  }
  Serial.println("\n[FIREBASE] Signed in & ready");

  // ── Read or initialise label ──
  currentLabel = fetchOrInitLabel();

  // ── Write initial status based on sensor reading ──
  carPresent = readUltrasonic();
  currentStatus = carPresent ? "busy" : "free";
  writeStatus(currentStatus);
  updateLED(carPresent);
  lcdShow(currentLabel, currentStatus);
  lastCarPresent = carPresent;

  Serial.println("[BOOT] Complete — Label=" + currentLabel + "  Status=" + currentStatus);

  // ── Start real-time stream on label path ──
  if (!Firebase.RTDB.beginStream(&fbStream, labelPath().c_str())) {
    Serial.println("[STREAM] Failed to start: " + fbStream.errorReason());
  } else {
    Serial.println("[STREAM] Listening on: " + labelPath());
    Firebase.RTDB.setStreamCallback(&fbStream, onLabelStream, onStreamTimeout);
  }

  // ── Start real-time stream on booked path ──
  if (!Firebase.RTDB.beginStream(&bookStream, bookPath().c_str())) {
    Serial.println("[STREAM] Failed to start: " + bookStream.errorReason());
  } else {
    Serial.println("[STREAM] Listening on: " + bookPath());
    Firebase.RTDB.setStreamCallback(&bookStream, onBookedStream, onStreamTimeout);
  }
}

// ══════════════════════════════════════════════
//  LOOP
// ══════════════════════════════════════════════
void loop() {
  carPresent = readUltrasonic();

  if (carPresent != lastCarPresent) {
    currentStatus = carPresent ? "busy" : "free";
    Serial.println("[STATUS CHANGE] " + String(lastCarPresent ? "busy" : "free") + " → " + currentStatus);

    writeStatus(currentStatus);
    updateLED(carPresent);
    beepStatusChange();
    lcdShow(currentLabel, currentStatus + userId);

    lastCarPresent = carPresent;
  }

  checkBooking();
}

// ══════════════════════════════════════════════
//  RTDB — WRITE STATUS
// ══════════════════════════════════════════════
void writeStatus(String status) {
  Serial.println("[RTDB] Writing status → " + status);

  if (Firebase.RTDB.setString(&fbWrite, statusPath().c_str(), status)) {
    Serial.println("[RTDB] Status written OK");
  } else {
    Serial.println("[RTDB] Write failed: " + fbWrite.errorReason());
  }
}

// ══════════════════════════════════════════════
//  RTDB — FETCH LABEL (write default if absent)
// ══════════════════════════════════════════════
String fetchOrInitLabel() {
  Serial.println("[RTDB] Fetching label from: " + labelPath());

  if (Firebase.RTDB.getString(&fbWrite, labelPath().c_str())) {
    String lbl = fbWrite.stringData();

    if (lbl.length() > 0) {
      Serial.println("[RTDB] Label found: " + lbl);
      return lbl;
    }

    // Node exists but is empty
    Serial.println("[RTDB] Label node empty, writing default");
    return "not configured";

  } else {
    // Node does not exist
    Serial.println("[RTDB] Label not found (" + fbWrite.errorReason() + "), writing default");
    return "not configured";
  }
}

String readUserId(FirebaseData &fb, String path) {
  if (!Firebase.RTDB.getString(&fb, path)) {
    Serial.println("❌ Failed to read from Firebase");
    return "";
  }

  String value = fb.stringData();

  // لو فاضية
  if (value.length() == 0) {
    return "";
  }

  // لو أقل من 4 حروف → رجعها كلها
  if (value.length() < 4) {
    return value;
  }

  // رجع أول 4 حروف
  return value.substring(0, 4);
}

// ══════════════════════════════════════════════
//  ULTRASONIC — returns true if car is detected
// ══════════════════════════════════════════════
bool readUltrasonic() {
  const int samples = 5;
  int validCount = 0;
  float sum = 0;

  for (int i = 0; i < samples; i++) {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);

    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    long duration = pulseIn(ECHO_PIN, HIGH, 30000);
    int distance = duration * 0.034 / 2;

    // Filter invalid readings
    if (distance > 2 && distance < 500) {
      sum += distance;
      validCount++;
    }

    delay(50);  // allow sensor to settle
  }

  if (validCount == 0) {
    Serial.println("[ULTRASONIC] Invalid reading");
    return false;
  }

  int avgDistance = sum / validCount;

  Serial.println("[ULTRASONIC] Avg Distance: " + String(avgDistance) + " cm");

  return (avgDistance > 0 && avgDistance <= CAR_DISTANCE_CM);
}

// ══════════════════════════════════════════════
//  LCD
// ══════════════════════════════════════════════
void lcdShow(String line1, String line2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1);
  lcd.setCursor(0, 1);
  lcd.print(line2);
  Serial.println("[LCD] '" + line1 + "' | '" + line2 + "'");
}

// ══════════════════════════════════════════════
//  RGB LED
// ══════════════════════════════════════════════
void updateLED(bool busy) {
  digitalWrite(LED_RED_PIN, busy ? HIGH : LOW);
  digitalWrite(LED_GREEN_PIN, busy ? LOW : HIGH);
  Serial.println("[LED] " + String(busy ? "RED (busy)" : "GREEN (free)"));
}

// ══════════════════════════════════════════════
//  BUZZER — 2 quick beeps on every status change
// ══════════════════════════════════════════════
void beepStatusChange() {
  Serial.println("[BUZZER] 2 beeps");
  for (int i = 0; i < 2; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    delay(100);
  }
}

// ══════════════════════════════════════════════
//  WIFI
// ══════════════════════════════════════════════
void connectWiFi() {
  Serial.print("[WIFI] Connecting to " + String(WIFI_SSID));
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lcdShow("Connecting WiFi", "");

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Connected — IP: " + WiFi.localIP().toString());
    lcdShow("WiFi OK", WiFi.localIP().toString());
    delay(1000);
  } else {
    Serial.println("\n[WIFI] FAILED — check credentials");
    lcdShow("WiFi FAILED", "Check config");
    delay(3000);
  }
}

time_t parseFirebaseTime(String isoTime) {
  struct tm t;

  sscanf(isoTime.c_str(),
         "%d-%d-%dT%d:%d:%d",
         &t.tm_year,
         &t.tm_mon,
         &t.tm_mday,
         &t.tm_hour,
         &t.tm_min,
         &t.tm_sec);

  t.tm_year -= 1900;  // important
  t.tm_mon -= 1;

  return mktime(&t);
}

bool isAfter10Minutes(time_t bookedTime) {
  time_t now = time(nullptr);
  double diff = difftime(now, bookedTime);
  return diff >= 20;  // 600 seconds = 10 minutes
}

void checkBooking() {
  if (isAfter10Minutes(bookedTime) && !timerFinished) {
    timerFinished = true;
    Serial.println("⏰ 10 minutes passed → Execute action");
    userId = "";
    lcdShow(currentLabel, "available");
  }
}
