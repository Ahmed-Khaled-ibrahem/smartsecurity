#include <Wire.h>
#include <SensirionI2cScd4x.h>

SensirionI2cScd4x scd4x;

uint16_t lastCo2 = 0;

void init_co2_sensor() {
  Wire.begin();
  Wire.setClock(100000);  // 100 kHz

  // Initialize SCD41 driver
  scd4x.begin(Wire, SCD41_I2C_ADDR_62);

  delay(1000);  // Wait after power-up

  // Stop any previous measurement
  err = scd4x.stopPeriodicMeasurement();
  Serial.print("stopPeriodicMeasurement() Error: ");
  Serial.print(err);
  Serial.print(" (0x");
  Serial.print(err, HEX);
  Serial.println(")");

  delay(500);
  
  // Read serial number
  uint64_t serialNumber;
  int16_t err = scd4x.getSerialNumber(serialNumber);

  Serial.print("getSerialNumber() Error: ");
  Serial.print(err);
  Serial.print(" (0x");
  Serial.print(err, HEX);
  Serial.println(")");

  if (err == 0) {
    Serial.print("Serial Number: 0x");
    Serial.println((unsigned long long)serialNumber, HEX);
  } else {
    Serial.println("Failed to communicate with SCD41.");
    return;
  }

  // Start measurements
  err = scd4x.startPeriodicMeasurement();

  Serial.print("startPeriodicMeasurement() Error: ");
  Serial.print(err);
  Serial.print(" (0x");
  Serial.print(err, HEX);
  Serial.println(")");

  if (err == 0) {
    Serial.println("SCD41 measurement started successfully.");
  } else {
    Serial.println("Failed to start periodic measurement.");
  }

  Serial.println("--------------------------------");
}

uint16_t read_co2() {
  bool dataReady = false;
  uint16_t err = scd4x.getDataReadyStatus(dataReady);

  if (err) {
    Serial.print("getDataReadyStatus Error: ");
    Serial.println(err);
    return lastCo2;
  }

  if (dataReady) {
    uint16_t co2;
    float temperature;
    float humidity;

    err = scd4x.readMeasurement(co2, temperature, humidity);

    if (err == 0 && co2 != 0) {
      lastCo2 = co2;

      Serial.print("CO2: ");
      Serial.print(co2);
      Serial.print(" ppm | Temp: ");
      Serial.print(temperature);
      Serial.print(" °C | Humidity: ");
      Serial.print(humidity);
      Serial.println(" %");
    } else {
      Serial.print("readMeasurement Error: ");
      Serial.println(err);
    }
  } else {
    Serial.println("Measurement not ready.");
  }

  return lastCo2;
}

void test_co2_sensor() {
  delay(2000);

  init_co2_sensor();

  while (true) {
    read_co2();
    delay(2000);
  }
}
