#include <WiFi.h>
#include <Firebase_ESP_Client.h>
#include <addons/TokenHelper.h>
#include <addons/RTDBHelper.h>
#include <DHT.h>
#include <HX711.h>
#include <time.h>
#include <UniversalTelegramBot.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define LCD_ADDRESS 0x27
#define LCD_COLS 16
#define LCD_ROWS 2

LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

bool isTesting = false;
// https://api.telegram.org/bot8268822841:AAFIb7dUXPMNk3soX9d0TmtVxMzk6S-2RH4/getUpdates
// ─── WiFi ────────────────────────────────────────────────────
#define WIFI_SSID "Orange-Fast"
#define WIFI_PASSWORD "#1288534459&4274321#Aa"

// ─── Firebase ────────────────────────────────────────────────
#define FIREBASE_API_KEY "AIzaSyCWLzqZlfJQJF0rc6n5_AjPKILrdEx1lYY"
#define FIREBASE_DATABASE_URL "https://doma-446607-default-rtdb.firebaseio.com"
#define FIREBASE_USER_EMAIL "esp32@gmail.com"
#define FIREBASE_USER_PASSWORD "12345678"

// ─── DHT ─────────────────────────────────────────────────────
#define DHT_PIN 4
#define DHT_TYPE DHT22  // change to DHT11 if needed
// ─── HX711 ───────────────────────────────────────────────────
#define HX711_DOUT 16
#define HX711_SCK 17
// ─── NTP ─────────────────────────────────────────────────────
#define NTP_SERVER "pool.ntp.org"
#define UTC_OFFSET 10800  // UTC+2 in seconds
// ─── Timing ──────────────────────────────────────────────────
#define DHT_INTERVAL_MS 8000
#define WEIGHT_INTERVAL_MS 500
#define DEBOUNCE_DELAY_MS 2000

// ─── Telegram ────────────────────────────────────────────────
#define TELEGRAM_RATE_LIMIT_MS 3000

// ─── Firebase objects ────────────────────────────────────────
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// ─── Sensor objects ──────────────────────────────────────────
DHT dht(DHT_PIN, DHT_TYPE);
HX711 scale;

// ─── ESP identity ────────────────────────────────────────────
String espId;  // derived from MAC address

// ─── Shelf config (loaded from Firebase) ─────────────────────
struct ShelfConfig {
  String name;
  String type;     // "solid" or "liquid"
  float itemSize;  // weight per item (g) or volume per item (ml)
  float price;
  int alertLimit;
  String telegramChatId;
  String telegramBotToken;
  float calibrationFactor;
  float shelfWeight;  // tare weight of empty shelf
};

// ─── History bounds (loaded from Firebase) ───────────────────
struct HistoryBounds {
  float maxTemp;
  float minTemp;
  float maxHumidity;
  float minHumidity;
};

WiFiClientSecure client;
ShelfConfig cfg;
HistoryBounds history;

// ─── Runtime state ───────────────────────────────────────────
int currentItemCount = 0;
int pendingItemCount = 0;
float currentLoad = 0.0f;
bool configLoaded = false;
bool firebaseReady = false;

unsigned long lastDhtUpdate = 0;
unsigned long lastWeightRead = 0;
unsigned long weightChangeTime = 0;  // when weight first changed
unsigned long lastTelegramSent = 0;
bool weightChangePending = false;
bool isFirstTime = true;

// ============================================================
//  UTILITY — ESP ID from MAC
// ============================================================

String getEspId() {
  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_WIFI_STA);  // read WiFi MAC
  char buf[18];                         // 6 bytes × 2 hex + 1 null terminator = 13, but 18 is safe
  snprintf(buf, sizeof(buf), "ESP_%02X%02X%02X%02X%02X%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return String(buf);
}

// ============================================================
//  UTILITY — NTP timestamp string  "YYYY-MM-DD HH:MM:SS"
// ============================================================
String getTimestamp() {
  struct tm ti;
  if (!getLocalTime(&ti)) {
    Serial.println("[NTP] Failed to get time");
    return "unknown";
  }
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &ti);
  return String(buf);
}

// ============================================================
//  WIFI — connect / reconnect
// ============================================================
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lcdPrint("Connecting ...", WIFI_SSID);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] Connected — IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WiFi] Connection failed — will retry later");
    lcdPrint("not connected", WIFI_SSID);
  }
}

// ============================================================
//  FIREBASE — initialise
// ============================================================
void initFirebase() {
  config.api_key = FIREBASE_API_KEY;
  config.database_url = FIREBASE_DATABASE_URL;
  auth.user.email = FIREBASE_USER_EMAIL;
  auth.user.password = FIREBASE_USER_PASSWORD;
  config.token_status_callback = tokenStatusCallback;

  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  Serial.println("[Firebase] Initialised — waiting for auth token...");

  // Wait up to 10 s for token
  unsigned long start = millis();
  while (!Firebase.ready() && millis() - start < 10000) {
    delay(200);
    Serial.print(".");
  }
  Serial.println();

  if (Firebase.ready()) {
    firebaseReady = true;
    Serial.println("[Firebase] Auth token OK");
  } else {
    Serial.println("[Firebase] Auth failed — check credentials");
  }
}

// ============================================================
//  FIREBASE — load config from  /<espId>/config
// ============================================================
bool loadConfig() {
  Serial.println("[Config] Loading shelf configuration from Firebase...");

  String basePath = "/" + espId + "/config";

  // Helper lambda to read a string field
  auto readStr = [&](const char* key, String& dest) -> bool {
    if (Firebase.RTDB.getString(&fbdo, basePath + "/" + key)) {
      dest = fbdo.stringData();
      Serial.printf("[Config]   %s = %s\n", key, dest.c_str());
      return true;
    }
    Serial.printf("[Config]   ERROR reading %s: %s\n", key, fbdo.errorReason().c_str());
    return false;
  };

  auto readFloat = [&](const char* key, float& dest) -> bool {
    if (Firebase.RTDB.getFloat(&fbdo, basePath + "/" + key)) {
      dest = fbdo.floatData();
      Serial.printf("[Config]   %s = %.4f\n", key, dest);
      return true;
    }
    Serial.printf("[Config]   ERROR reading %s: %s\n", key, fbdo.errorReason().c_str());
    return false;
  };

  auto readInt = [&](const char* key, int& dest) -> bool {
    if (Firebase.RTDB.getInt(&fbdo, basePath + "/" + key)) {
      dest = fbdo.intData();
      Serial.printf("[Config]   %s = %d\n", key, dest);
      return true;
    }
    Serial.printf("[Config]   ERROR reading %s: %s\n", key, fbdo.errorReason().c_str());
    return false;
  };

  bool ok = true;
  ok &= readStr("name", cfg.name);
  ok &= readStr("type", cfg.type);
  ok &= readFloat("item_size", cfg.itemSize);
  ok &= readFloat("price", cfg.price);
  ok &= readInt("alert_limit", cfg.alertLimit);
  ok &= readStr("telegram_chat_id", cfg.telegramChatId);
  ok &= readStr("telegram_bot_token", cfg.telegramBotToken);
  ok &= readFloat("calibration_factor", cfg.calibrationFactor);
  ok &= readFloat("shelf_weight", cfg.shelfWeight);

  if (!ok) {
    Serial.println("[Config] One or more fields failed to load");
    return false;
  }
  Serial.println("[Config] Configuration loaded successfully");
  return true;
}

// ============================================================
//  FIREBASE — load history bounds from  /<espId>/history
// ============================================================
bool loadHistoryBounds() {
  Serial.println("[History] Loading history bounds from Firebase...");

  String basePath = "/" + espId + "/history";

  auto readFloat = [&](const char* key, float& dest) -> bool {
    if (Firebase.RTDB.getFloat(&fbdo, basePath + "/" + key)) {
      dest = fbdo.floatData();
      Serial.printf("[History]   %s = %.2f\n", key, dest);
      return true;
    }
    Serial.printf("[History]   ERROR reading %s: %s\n", key, fbdo.errorReason().c_str());
    return false;
  };

  bool ok = true;
  ok &= readFloat("max_temp", history.maxTemp);
  ok &= readFloat("min_temp", history.minTemp);
  ok &= readFloat("max_humidity", history.maxHumidity);
  ok &= readFloat("min_humidity", history.minHumidity);

  if (!ok) {
    Serial.println("[History] Warning: Some history bounds could not be loaded — using defaults");
    // Non-fatal: default to extreme values so any reading updates them
    history.maxTemp = -999;
    history.minTemp = 999;
    history.maxHumidity = -999;
    history.minHumidity = 999;
  }
  return true;
}

// ============================================================
//  DHT — read and push to Firebase
// ============================================================
void updateDHTReading() {
  float temp = 0;
  float hum = 0;

  if (isTesting) {
    float number = random(0, 100);
    temp = number;
    hum = number + 10;
  } else {
    temp = dht.readTemperature();
    hum = dht.readHumidity();

    if (isnan(temp) || isnan(hum)) {
      Serial.println("[DHT] Read failed — sensor might be disconnected");
      return;
    }
  }

  Serial.printf("[DHT] Temp: %.1f°C  Humidity: %.1f%%\n", temp, hum);

  // Update history bounds
  bool historyChanged = false;
  if (temp > history.maxTemp) {
    history.maxTemp = temp;
    historyChanged = true;
  }
  if (temp < history.minTemp) {
    history.minTemp = temp;
    historyChanged = true;
  }
  if (hum > history.maxHumidity) {
    history.maxHumidity = hum;
    historyChanged = true;
  }
  if (hum < history.minHumidity) {
    history.minHumidity = hum;
    historyChanged = true;
  }

  String basePath = "/" + espId + "/readings";
  String histPath = "/" + espId + "/history";
  String timestamp = getTimestamp();

  // Push current readings
  Firebase.RTDB.setFloat(&fbdo, basePath + "/temperature", temp) || Serial.printf("[DHT] Firebase write temp failed: %s\n", fbdo.errorReason().c_str());
  Firebase.RTDB.setFloat(&fbdo, basePath + "/humidity", hum) || Serial.printf("[DHT] Firebase write hum failed: %s\n", fbdo.errorReason().c_str());
  Firebase.RTDB.setString(&fbdo, basePath + "/last_update", timestamp) || Serial.printf("[DHT] Firebase write time failed: %s\n", fbdo.errorReason().c_str());

  // Push updated history bounds if changed
  if (historyChanged) {
    Firebase.RTDB.setFloat(&fbdo, histPath + "/max_temp", history.maxTemp);
    Firebase.RTDB.setFloat(&fbdo, histPath + "/min_temp", history.minTemp);
    Firebase.RTDB.setFloat(&fbdo, histPath + "/max_humidity", history.maxHumidity);
    Firebase.RTDB.setFloat(&fbdo, histPath + "/min_humidity", history.minHumidity);
    Serial.println("[DHT] History bounds updated on Firebase");
  }
}

// ============================================================
//  HX711 — read net load and convert to item count
// ============================================================
float readNetLoad() {
  if (!scale.is_ready()) {
    Serial.println("[HX711] Scale not ready");
    return currentLoad;
  }

  float raw = scale.get_units(5);     // average 5 readings
  float net = raw - cfg.shelfWeight;  // subtract empty shelf tare
  if (net < 0) net = 0;

  Serial.printf("[HX711] Raw: %.2fg  Net: %.2fg\n", raw, net);
  return net;
}

int loadToItemCount(float netLoad) {
  if (cfg.itemSize <= 0) {
    Serial.println("[Items] item_size is 0 — cannot calculate count");
    return 0;
  }
  return (int)round(netLoad / cfg.itemSize);
}

// ============================================================
//  FIREBASE — push item count update
// ============================================================
void pushItemCountToFirebase(int count, float load) {
  String basePath = "/" + espId + "/readings";

  Serial.printf("[Firebase] Pushing item count: %d  load: %.2fg\n", count, load);

  Firebase.RTDB.setInt(&fbdo, basePath + "/item_count", count) || Serial.printf("[Items] Write count failed: %s\n", fbdo.errorReason().c_str());
  Firebase.RTDB.setFloat(&fbdo, basePath + "/current_load", load) || Serial.printf("[Items] Write load failed: %s\n", fbdo.errorReason().c_str());
}

// ============================================================
//  FIREBASE — log transaction to /transactions
// ============================================================
void logTransaction(int delta) {
  String type = (delta > 0) ? "plus" : "minus";
  int amount = abs(delta);

  Serial.printf("[Transaction] %s %d × %s\n", type.c_str(), amount, cfg.name.c_str());

  String txPath = "/transactions";

  FirebaseJson json;
  json.set("esp_id", espId);
  json.set("name", cfg.name);
  json.set("date", getTimestamp());
  json.set("type", type);
  json.set("amount", amount);

  if (Firebase.RTDB.pushJSON(&fbdo, txPath, &json)) {
    Serial.printf("[Transaction] Logged with key: %s\n", fbdo.pushName().c_str());
  } else {
    Serial.printf("[Transaction] Failed: %s\n", fbdo.errorReason().c_str());
  }
}

// ============================================================
//  TELEGRAM — send alert message
// ============================================================
void sendTelegramAlert(int count) {

  static UniversalTelegramBot bot(cfg.telegramBotToken, client);
  // Rate limiting
  unsigned long now = millis();
  if (now - lastTelegramSent < TELEGRAM_RATE_LIMIT_MS) {
    Serial.println("[Telegram] Rate limited — skipping alert");
    return;
  }

  if (cfg.telegramBotToken.isEmpty() || cfg.telegramChatId.isEmpty()) {
    Serial.println("[Telegram] Bot token or chat ID not set — skipping");
    return;
  }

  String msg = "⚠️ *Stock Alert* ⚠️\n";
  msg += "Shelf: *" + cfg.name + "*\n";
  msg += "Items remaining: *" + String(count) + "*\n";
  msg += "Alert limit: " + String(cfg.alertLimit) + "\n";
  msg += "Time: " + getTimestamp();

  bool result = bot.sendMessage(cfg.telegramChatId, msg, "");

  if (result) {
    Serial.println("[Telegram] Alert sent successfully");
    lastTelegramSent = now;
  } else {
    Serial.printf("[Telegram] Failed ");
    Serial.println(result);
  }
}

// ============================================================
//  WEIGHT — main polling logic with debounce
// ============================================================
void handleWeightReading() {
  float netLoad = 0;

  if (isTesting) {
    netLoad = analogRead(34);
  } else {
    netLoad = readNetLoad();
  }

  int newCount = loadToItemCount(netLoad);

  if (isFirstTime) {
    isFirstTime = false;
    currentItemCount = newCount;
  }

  if (newCount == currentItemCount && !weightChangePending) {
    return;  // nothing changed
  }

  if (newCount != pendingItemCount) {
    // Weight is still in flux — restart debounce window
    pendingItemCount = newCount;
    weightChangeTime = millis();
    weightChangePending = true;
    Serial.printf("[Debounce] Weight changed → %d items — waiting for stable reading...\n", newCount);
    return;
  }

  // Same pending count — check if debounce window has passed
  if (weightChangePending && (millis() - weightChangeTime >= DEBOUNCE_DELAY_MS)) {
    int delta = pendingItemCount - currentItemCount;

    if (delta == 0) {
      weightChangePending = false;
      return;
    }

    Serial.printf("[Items] Stable change detected: %d → %d (delta %+d)\n",
                  currentItemCount, pendingItemCount, delta);

    currentItemCount = pendingItemCount;
    currentLoad = netLoad;
    weightChangePending = false;

    pushItemCountToFirebase(currentItemCount, currentLoad);
    logTransaction(delta);

    if (currentItemCount <= cfg.alertLimit) {
      Serial.printf("[Alert] Item count %d ≤ alert limit %d — sending Telegram\n",
                    currentItemCount, cfg.alertLimit);
      sendTelegramAlert(currentItemCount);
    }
  }
}

void lcdPrint(String line1, String line2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1);

  lcd.setCursor(0, 1);
  lcd.print(line2);
}

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  Serial.println("\n====================================");
  Serial.println("  Smart Shelf — Booting");
  Serial.println("====================================");
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcdPrint("Smart Shelf", "Booting");
  delay(200);

  espId = getEspId();
  Serial.printf("[System] ESP ID: %s\n", espId.c_str());

  // WiFi
  connectWiFi();
  client.setInsecure();

  // NTP
  lcdPrint("Time Sync", "Loading ...");
  configTime(UTC_OFFSET, 0, NTP_SERVER);
  Serial.println("[NTP] Synchronising time ...");

  struct tm timeinfo;
  int attempts = 0;
  while (!getLocalTime(&timeinfo) && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
    if (attempts > 30) {
      lcdPrint("Please Restart", "The Device");
      Serial.println("Please Restart the device");
    }
  }
  Serial.println();

  if (getLocalTime(&timeinfo)) {
    Serial.printf("[NTP] Time: %s\n", getTimestamp().c_str());
    lcdPrint("Time : ", getTimestamp().c_str());
  } else {
    Serial.println("[NTP] Failed to get time — check WiFi/NTP server");
  }

  lcdPrint("Reading Database", "Loading ...");
  // Firebase
  initFirebase();

  if (firebaseReady) {
    String _path = "/" + espId + "/anchor";
    Firebase.RTDB.setString(&fbdo, _path + "/anchor", "esp") || Serial.printf("[DHT] Firebase write anchor failed: %s\n", fbdo.errorReason().c_str());

    loadConfig();
    loadHistoryBounds();
    configLoaded = true;
  } else {
    Serial.println("[Setup] Firebase not ready — running without config");
  }
  lcdPrint("Checking Sensors", "Loading ...");
  // DHT
  dht.begin();
  Serial.println("[DHT] Sensor initialised");

  // HX711
  scale.begin(HX711_DOUT, HX711_SCK);
  if (scale.is_ready()) {
    scale.set_scale(cfg.calibrationFactor);
    scale.tare();
    Serial.printf("[HX711] Scale ready — calibration factor: %.2f\n", cfg.calibrationFactor);
  } else {
    Serial.println("[HX711] WARNING: Scale not responding — check wiring");
  }

  // Read initial item count
  currentLoad = readNetLoad();
  currentItemCount = loadToItemCount(currentLoad);
  pendingItemCount = currentItemCount;
  Serial.printf("[Items] Initial count: %d  load: %.2fg\n", currentItemCount, currentLoad);

  Serial.println("[Setup] Boot complete — entering main loop");
  Serial.println("====================================\n");
}

// ============================================================
//  LOOP
// ============================================================
void loop() {
  unsigned long now = millis();

  // ── WiFi watchdog ──────────────────────────────────────────
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Connection lost — attempting reconnect...");
    connectWiFi();
    if (WiFi.status() == WL_CONNECTED && !firebaseReady) {
      initFirebase();
      if (firebaseReady && !configLoaded) {
        loadConfig();
        loadHistoryBounds();
        configLoaded = true;
      }
    }
    return;  // skip sensor reads until reconnected
  }

  // ── DHT every 3 seconds ───────────────────────────────────
  if (configLoaded && (now - lastDhtUpdate >= DHT_INTERVAL_MS)) {
    lastDhtUpdate = now;
    updateDHTReading();
    lcdPrint(cfg.name, String(cfg.price));
  }

  // ── Weight every 500 ms ───────────────────────────────────
  if (configLoaded && (now - lastWeightRead >= WEIGHT_INTERVAL_MS)) {
    lastWeightRead = now;
    handleWeightReading();
  }

  delay(10);
}
