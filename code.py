#include <SoftwareSerial.h>

#define PIN_SIM_RX 10  // Arduino RX  <- SIM800L TX
#define PIN_SIM_TX 11  // Arduino TX  -> SIM800L RX

#define SMS_PHONE_NUMBER "+201XXXXXXXXX"

SoftwareSerial sim800l(PIN_SIM_RX, PIN_SIM_TX);

bool smsSent = false;

void printResponse(unsigned long timeoutMs) {
  unsigned long started = millis();

  while (millis() - started < timeoutMs) {
    while (sim800l.available()) {
      Serial.write(sim800l.read());
    }
  }

  Serial.println();
}

void simSendAT(const char *command, unsigned long timeoutMs = 1500) {
  Serial.print(F("\n>> "));
  Serial.println(command);

  sim800l.println(command);
  printResponse(timeoutMs);
}

bool isRegistered() {
  sim800l.println(F("AT+CREG?"));

  String response;
  unsigned long started = millis();

  while (millis() - started < 3000) {
    while (sim800l.available()) {
      char c = sim800l.read();
      Serial.write(c);
      response += c;
    }
  }

  return response.indexOf(F("+CREG: 0,1")) >= 0 ||
         response.indexOf(F("+CREG: 0,5")) >= 0;
}

void sendSMS(const char *phoneNumber, const char *message) {
  Serial.println(F("\n--- Sending SMS ---"));

  sim800l.println(F("AT+CMGF=1"));
  printResponse(1500);

  sim800l.print(F("AT+CMGS=\""));
  sim800l.print(phoneNumber);
  sim800l.println(F("\""));
  printResponse(2000);

  sim800l.print(message);
  sim800l.write(26); // Ctrl+Z sends the SMS
  printResponse(15000);
}

void setup() {
  Serial.begin(115200);
  sim800l.begin(9600);

  delay(5000);

  Serial.println(F("\nSIM800L test started"));

  simSendAT("AT");
  simSendAT("ATE0");
  simSendAT("AT+CPIN?");  // Must say: +CPIN: READY
  simSendAT("AT+CCID");
  simSendAT("AT+CSQ");
  simSendAT("AT+CREG?");
  simSendAT("AT+COPS?");

  // Automatic carrier selection; can take 30 seconds
  simSendAT("AT+COPS=0", 30000);
}

void loop() {
  Serial.println(F("\n========== NETWORK CHECK =========="));

  simSendAT("AT+CSQ");
  simSendAT("AT+CREG?");

  if (isRegistered()) {
    Serial.println(F("\nNetwork registered."));

    if (!smsSent) {
      sendSMS(SMS_PHONE_NUMBER, "SIM800L test message: module working.");
      smsSent = true;
    }
  } else {
    Serial.println(F("\nStill not registered. Check antenna and SIM800L power."));
  }

  delay(30000);
}
