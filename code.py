#include <Arduino.h>
#include <Wire.h>
#include <SensirionI2cScd4x.h>

#define SDA_PIN 21
#define SCL_PIN 22

#ifdef NO_ERROR
#undef NO_ERROR
#endif
#define NO_ERROR 0

SensirionI2cScd4x sensor;
static char errorMessage[64];
static int16_t error;

void printUint64(uint64_t& value) {
  Serial.print("0x");
  Serial.print((uint32_t)(value >> 32), HEX);
  Serial.print((uint32_t)(value & 0xFFFFFFFF), HEX);
}

// Manually toggles SCL to release any device stuck holding SDA low
void i2cBusRecovery(int sdaPin, int sclPin) {
  Serial.println("--- Running I2C bus recovery ---");
  pinMode(sdaPin, INPUT_PULLUP);
  pinMode(sclPin, OUTPUT);
  for (int i = 0; i < 9; i++) {
    digitalWrite(sclPin, HIGH);
    delayMicroseconds(5);
    digitalWrite(sclPin, LOW);
    delayMicroseconds(5);
  }
  pinMode(sclPin, INPUT_PULLUP);
  delay(10);
  Serial.println("--- Bus recovery complete ---");
}

// Full address scan, 0x08 to 0x77
void fullI2cScan() {
  Serial.println("--- Full I2C scan (0x08-0x77) ---");
  int found = 0;
  for (uint8_t addr = 0x08; addr <= 0x77; addr++) {
    Wire.beginTransmission(addr);
    uint8_t result = Wire.endTransmission();
    if (result == 0) {
      Serial.print("Device found at 0x");
      Serial.println(addr, HEX);
      found++;
    }
  }
  if (found == 0) {
    Serial.println("No devices found at all. Check wiring/power/pull-ups.");
  } else {
    Serial.print(found);
    Serial.println(" device(s) found.");
  }
  Serial.println("--- Scan complete ---");
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(100); }
  delay(1000); // let SCD41 finish power-up before touching the bus

  Serial.println();
  Serial.println("========== SCD41 DIAGNOSTIC START ==========");

  i2cBusRecovery(SDA_PIN, SCL_PIN);

  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);   // 100kHz, SCD41 spec-safe
  Wire.setTimeOut(1000);   // ms, survive long clock stretches

  fullI2cScan();

  // Manual raw ACK check at the SCD41 address
  Wire.beginTransmission(0x62);
  byte err = Wire.endTransmission();
  Serial.print("Manual ACK check at 0x62, result code = ");
  Serial.print(err);
  Serial.println(err == 0 ? "  (0 = ACK, good)" : "  (non-zero = NACK/error)");

  sensor.begin(Wire, SCD41_I2C_ADDR_62);

  Serial.println("--- wakeUp() ---");
  error = sensor.wakeUp();
  if (error != NO_ERROR) {
    Serial.print("wakeUp() error code: ");
    Serial.print(error);
    Serial.print("  message: ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
    Serial.println("(Note: SCD41 sometimes NACKs wakeUp() if already awake - this specific error is often safe to ignore.)");
  } else {
    Serial.println("wakeUp() OK");
  }
  delay(30);

  Serial.println("--- stopPeriodicMeasurement() ---");
  error = sensor.stopPeriodicMeasurement();
  if (error != NO_ERROR) {
    Serial.print("stopPeriodicMeasurement() error code: ");
    Serial.print(error);
    Serial.print("  message: ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
  } else {
    Serial.println("stopPeriodicMeasurement() OK");
  }
  delay(500); // datasheet: stop_periodic_measurement needs ~500ms execution time

  Serial.println("--- reinit() ---");
  error = sensor.reinit();
  if (error != NO_ERROR) {
    Serial.print("reinit() error code: ");
    Serial.print(error);
    Serial.print("  message: ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
  } else {
    Serial.println("reinit() OK");
  }
  delay(30); // datasheet: reinit needs ~20ms execution time

  Serial.println("--- getSerialNumber() ---");
  uint64_t serialNumber = 0;
  error = sensor.getSerialNumber(serialNumber);
  if (error != NO_ERROR) {
    Serial.print("getSerialNumber() error code: ");
    Serial.print(error);
    Serial.print("  message: ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
    Serial.println("========== DIAGNOSTIC HALTED (cannot proceed without serial number) ==========");
    return;
  } else {
    Serial.print("Serial number: ");
    printUint64(serialNumber);
    Serial.println("  OK");
  }

  Serial.println("--- startPeriodicMeasurement() ---");
  error = sensor.startPeriodicMeasurement();
  if (error != NO_ERROR) {
    Serial.print("startPeriodicMeasurement() error code: ");
    Serial.print(error);
    Serial.print("  message: ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
    Serial.println("========== DIAGNOSTIC HALTED ==========");
    return;
  } else {
    Serial.println("startPeriodicMeasurement() OK");
  }

  Serial.println("========== SETUP COMPLETE - moving to loop() ==========");
}

void loop() {
  bool dataReady = false;
  uint16_t co2Concentration = 0;
  float temperature = 0.0;
  float relativeHumidity = 0.0;

  delay(5000);

  error = sensor.getDataReadyStatus(dataReady);
  if (error != NO_ERROR) {
    Serial.print("getDataReadyStatus() error code: ");
    Serial.print(error);
    Serial.print("  message: ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
    return;
  }

  if (!dataReady) {
    Serial.println("Data not ready yet, waiting...");
    return;
  }

  error = sensor.readMeasurement(co2Concentration, temperature, relativeHumidity);
  if (error != NO_ERROR) {
    Serial.print("readMeasurement() error code: ");
    Serial.print(error);
    Serial.print("  message: ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
    return;
  }

  Serial.print("CO2 [ppm]: ");
  Serial.print(co2Concentration);
  Serial.print("   Temp [C]: ");
  Serial.print(temperature);
  Serial.print("   RH [%]: ");
  Serial.println(relativeHumidity);
}
