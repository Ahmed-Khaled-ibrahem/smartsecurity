#define SOIL_DRY 3200
#define SOIL_WET 1200

#define SOIL_PIN 36

void init_soil_sensor() {
  pinMode(SOIL_PIN, INPUT);
}

float read_soil() {
  int raw = analogRead(SOIL_PIN);
  float percentage = map(raw, SOIL_DRY, SOIL_WET, 0, 100);
  percentage = constrain(percentage, 0, 100);
  return percentage;
}

void test_soil_sensor() {
  init_soil_sensor();

  while (1) {
    Serial.print("Current SOIL VALUE : ");
    Serial.println(read_soil());
    Serial.println(analogRead(SOIL_PIN));
    delay(2000);
  }
}
