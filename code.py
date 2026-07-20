#include <Wire.h>
#include <SensirionI2cScd4x.h>

// ---- CONFIG ----
#define SDA_PIN 21        // change to your actual SDA pin
#define SCL_PIN 22        // change to your actual SCL pin
#define I2C_CLOCK 100000  // SCD4x max supported speed is 100kHz

SensirionI2cScd4x scd4x;
static char errorMessage[64];
uint16_t lastCo2 = 0;

// ---------------------------------------------------
// I2C Scanner
// ---------------------------------------------------
void scanI2C() {
  Serial.println("\n--- Scanning I2C bus ---");
  int found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    uint8_t err = Wire.endTransmission();
    if (err == 0) {
      Serial.printf("Found device at 0x%02X\n", addr);
      found++;
    }
  }
  if (found == 0) {
    Serial.println("No I2C devices found. Check wiring, power, pull-ups.");
  } else {
    Serial.printf("Scan complete. %d device(s) found.\n", found);
  }
  Serial.println("------------------------\n");
}

// ---------------------------------------------------
// SCD41 Init
// ---------------------------------------------------
bool init_co2_sensor() {
  scd4x.begin(Wire, SCD41_I2C_ADDR_62);

  uint16_t err = scd4x.stopPeriodicMeasurement();
  if (err) {
    errorToString(err, errorMessage, sizeof(errorMessage));
    Serial.print("stopPeriodicMeasurement error: ");
    Serial.println(errorMessage);
  }
  delay(1000);

  uint64_t serialNumber = 0;
  err = scd4x.getSerialNumber(serialNumber);
  if (err) {
    errorToString(err, errorMessage, sizeof(errorMessage));
    Serial.print("getSerialNumber error: ");
    Serial.println(errorMessage);
    Serial.println("SCD41 not responding on the bus.");
    return false;
  }
  Serial.printf("SCD41 serial number: %012llX\n", serialNumber);

  err = scd4x.startPeriodicMeasurement();
  if (err) {
    errorToString(err, errorMessage, sizeof(errorMessage));
    Serial.print("startPeriodicMeasurement error: ");
    Serial.println(errorMessage);
    return false;
  }

  Serial.println("SCD41 periodic measurement started successfully.");
  return true;
}

// ---------------------------------------------------
// SCD41 Read
// ---------------------------------------------------
uint16_t read_co2() {
  bool dataReady = false;
  uint16_t err = scd4x.getDataReadyStatus(dataReady);
  if (err) {
    errorToString(err, errorMessage, sizeof(errorMessage));
    Serial.print("getDataReadyStatus error: ");
    Serial.println(errorMessage);
    return lastCo2;
  }

  if (!dataReady) {
    Serial.println("Data not ready yet...");
    return lastCo2;
  }

  uint16_t co2 = 0;
  float scdTemp = 0, scdHum = 0;
  err = scd4x.readMeasurement(co2, scdTemp, scdHum);
  if (err) {
    errorToString(err, errorMessage, sizeof(errorMessage));
    Serial.print("readMeasurement error: ");
    Serial.println(errorMessage);
    return lastCo2;
  }

  if (co2 != 0) {
    lastCo2 = co2;
    Serial.printf("CO2: %u ppm | Temp: %.2f C | Humidity: %.2f %%\n", co2, scdTemp, scdHum);
  } else {
    Serial.println("Read returned co2 = 0, ignoring.");
  }

  return lastCo2;
}

// ---------------------------------------------------
// Setup / Loop
// ---------------------------------------------------
bool sensorReady = false;

void setup() {
  Serial.begin(115200);
  delay(1000);  // let Serial settle on ESP32 boot

  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(I2C_CLOCK);

  scanI2C();

  sensorReady = init_co2_sensor();
  if (!sensorReady) {
    Serial.println("Sensor init failed. Check scan results above.");
  }
}

void loop() {
  if (sensorReady) {
    read_co2();
  } else {
    // retry scan + init every 5s if sensor wasn't found at boot
    scanI2C();
    sensorReady = init_co2_sensor();
  }
  delay(5000);  // SCD41 measures every 5s in periodic mode
}
