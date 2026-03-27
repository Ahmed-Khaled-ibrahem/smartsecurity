#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>

#define SOIL_SENSOR_PIN A0  // Capacitive Moisture Sensor (analog)
#define DHT_PIN 2           // DHT11 data pin
#define RELAY_PIN 7         // Relay IN pin (controls water pump)

#define DHT_TYPE DHT11
#define SOIL_DRY_VALUE 800  // Raw ADC value when completely dry
#define SOIL_WET_VALUE 300  // Raw ADC value when completely wet
#define MOISTURE_THRESHOLD 40  // percent (0–100)
#define READ_INTERVAL 2000
#define RELAY_ACTIVE_LOW true

LiquidCrystal_I2C lcd(0x27, 16, 2);  // Change 0x27 to 0x3F if LCD doesn't show
DHT dht(DHT_PIN, DHT_TYPE);

void pumpOn() {
  digitalWrite(RELAY_PIN, RELAY_ACTIVE_LOW ? LOW : HIGH);
}

void pumpOff() {
  digitalWrite(RELAY_PIN, RELAY_ACTIVE_LOW ? HIGH : LOW);
}

int rawToPercent(int raw) {
  int pct = map(raw, SOIL_DRY_VALUE, SOIL_WET_VALUE, 0, 100);
  return constrain(pct, 0, 100);
}

void setup() {
  Serial.begin(9600);
  Serial.println("=== Smart Irrigation System Starting ===");

  pinMode(RELAY_PIN, OUTPUT);
  pumpOff();
  Serial.println("[RELAY] Pump initialized OFF");

  dht.begin();
  Serial.println("[DHT11] Sensor initialized");

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("  Smart Plant  ");
  lcd.setCursor(0, 1);
  lcd.print("   Irrigator   ");
  Serial.println("[LCD] Display initialized");

  delay(2000);
  lcd.clear();
}

void loop() {
  static unsigned long lastRead = 0;

  if (millis() - lastRead < READ_INTERVAL) return;
  lastRead = millis();

  // ── Read Sensors ──────────────────────────
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  int soilRaw = analogRead(SOIL_SENSOR_PIN);
  int moisture = rawToPercent(soilRaw);

  // ── Validate DHT11 reading ─────────────────
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("[DHT11] ERROR: Failed to read sensor!");
    lcd.setCursor(0, 0);
    lcd.print("DHT11 Error!    ");
    return;
  }

  // ── Serial Debug Output ────────────────────
  Serial.println("──────────────────────────");
  Serial.print("[SOIL]  Raw ADC : ");
  Serial.println(soilRaw);
  Serial.print("[SOIL]  Moisture: ");
  Serial.print(moisture);
  Serial.println("%");
  Serial.print("[DHT11] Temp    : ");
  Serial.print(temperature);
  Serial.println(" °C");
  Serial.print("[DHT11] Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");
  Serial.print("[PUMP]  Threshold: ");
  Serial.print(MOISTURE_THRESHOLD);
  Serial.println("%");

  // ── Pump Control Logic ─────────────────────
  if (moisture < MOISTURE_THRESHOLD) {
    pumpOn();
    Serial.println("[PUMP]  Status  : ON  (soil too dry)");
  } else {
    pumpOff();
    Serial.println("[PUMP]  Status  : OFF (moisture OK)");
  }

  // ── Update LCD ─────────────────────────────
  // Line 1: Temperature and Humidity
  lcd.setCursor(0, 0);
  lcd.print("T:");
  lcd.print((int)temperature);
  lcd.print("C H:");
  lcd.print((int)humidity);
  lcd.print("%   ");  // trailing spaces to clear old chars

  // Line 2: Moisture and pump status
  lcd.setCursor(0, 1);
  lcd.print("Soil:");
  lcd.print(moisture);
  lcd.print("% ");
  lcd.print(moisture < MOISTURE_THRESHOLD ? "PUMP:ON " : "PUMP:OFF");
}
