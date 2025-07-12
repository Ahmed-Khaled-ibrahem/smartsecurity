const int trigPin = 8;
const int echoPin = 9;

const int motor1Pin1 = 2;
const int motor1Pin2 = 3;
const int motor2Pin1 = 4;
const int motor2Pin2 = 5;
const int enable1Pin = 6;
const int enable2Pin = 7;

const int relayPin = 10;

const int carSpeed = 150;     // Range: 0 - 255
const int stopDistance = 20;  // cm

bool startSequence = false;

const int buttonPin = 11;

void setup() {

  Serial.begin(9600);

  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  pinMode(buttonPin, INPUT);

  pinMode(motor1Pin1, OUTPUT);
  pinMode(motor1Pin2, OUTPUT);
  pinMode(motor2Pin1, OUTPUT);
  pinMode(motor2Pin2, OUTPUT);
  pinMode(enable1Pin, OUTPUT);
  pinMode(enable2Pin, OUTPUT);

  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, LOW);
  Serial.println("Code is starting");
}


void loop() {
  handleButtonPress();
  if (startSequence) {
    moveForward(carSpeed);
    long distance = getDistance();

    if (distance <= stopDistance) {
      stopMotors();
      delay(500);
      digitalWrite(relayPin, HIGH);
      startSequence = false;
    }
  }
}


void handleButtonPress() {

  if (digitalRead(buttonPin) == HIGH) {
    while (digitalRead(buttonPin) == HIGH) {
      delay(5);
    }
    startSequence = true;
    Serial.println("Button pressed. Starting sequence...");
  }
}

long getDistance() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH);
  long distanceCm = duration * 0.034 / 2;

  Serial.print("Distance: ");
  Serial.print(distanceCm);
  Serial.println(" cm");

  return distanceCm;
}

void moveForward(int speed) {
  digitalWrite(motor1Pin1, HIGH);
  digitalWrite(motor1Pin2, LOW);
  digitalWrite(motor2Pin1, HIGH);
  digitalWrite(motor2Pin2, LOW);

  analogWrite(enable1Pin, speed);
  analogWrite(enable2Pin, speed);
}

void stopMotors() {
  digitalWrite(motor1Pin1, LOW);
  digitalWrite(motor1Pin2, LOW);
  digitalWrite(motor2Pin1, LOW);
  digitalWrite(motor2Pin2, LOW);

  analogWrite(enable1Pin, 0);
  analogWrite(enable2Pin, 0);
}
