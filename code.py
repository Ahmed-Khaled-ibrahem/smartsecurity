#include <SoftwareSerial.h>

#define PIN_SIM_RX 10  // Arduino RX  <- SIM800L TX
#define PIN_SIM_TX 11  // Arduino TX  -> SIM800L RX
#define SMS_PHONE_NUMBER "+201XXXXXXXXX"

SoftwareSerial sim800l(PIN_SIM_RX, PIN_SIM_TX);

bool smsSent = false;

// ---------- Low level helpers ----------

// Reads whatever the module sends for timeoutMs, echoes to Serial,
// and returns everything captured (bounded length to protect RAM).
String readResponse(unsigned long timeoutMs, size_t maxLen = 300) {
  String response;
  unsigned long started = millis();
  while (millis() - started < timeoutMs) {
    while (sim800l.available()) {
      char c = sim800l.read();
      Serial.write(c);
      if (response.length() < maxLen) response += c;
    }
  }
  Serial.println();
  return response;
}

// Sends an AT command, waits, and tells you PASS/FAIL against an
// expected substring. Returns true if expected text was found.
bool simSendAT(const char *command, const char *expect = "OK",
               unsigned long timeoutMs = 1500) {
  Serial.print(F("\n>> "));
  Serial.println(command);
  sim800l.println(command);
  String resp = readResponse(timeoutMs);

  bool ok = resp.indexOf(expect) >= 0;
  Serial.print(F("   [" ));
  Serial.print(ok ? F("PASS") : F("FAIL"));
  Serial.print(F("] expected \""));
  Serial.print(expect);
  Serial.println(F("\""));
  return ok;
}

// Waits specifically for the '>' SMS prompt instead of a fixed delay.
// Returns true if '>' showed up before timeout.
bool waitForPrompt(unsigned long timeoutMs = 5000) {
  unsigned long started = millis();
  while (millis() - started < timeoutMs) {
    while (sim800l.available()) {
      char c = sim800l.read();
      Serial.write(c);
      if (c == '>') return true;
    }
  }
  return false;
}

// ---------- Diagnostic steps ----------

bool checkModuleAlive() {
  Serial.println(F("\n[STEP] Module responding to AT?"));
  return simSendAT("AT");
}

bool checkSimInserted() {
  Serial.println(F("\n[STEP] SIM card present / unlocked?"));
  sim800l.println(F("AT+CPIN?"));
  String resp = readResponse(2000);
  if (resp.indexOf("READY") >= 0) {
    Serial.println(F("   [PASS] SIM ready, no PIN needed"));
    return true;
  }
  if (resp.indexOf("SIM PIN") >= 0) {
    Serial.println(F("   [FAIL] SIM is PIN-locked. Send AT+CPIN=\"yourpin\" or remove the PIN using a phone first."));
  } else if (resp.indexOf("+CME ERROR") >= 0) {
    Serial.println(F("   [FAIL] CME ERROR - check SIM card is inserted correctly and contacts are clean."));
  } else {
    Serial.println(F("   [FAIL] No valid CPIN response - check wiring/power."));
  }
  return false;
}

int checkSignalQuality() {
  Serial.println(F("\n[STEP] Signal quality (CSQ)"));
  sim800l.println(F("AT+CSQ"));
  String resp = readResponse(1500);
  int idx = resp.indexOf("+CSQ:");
  int rssi = -1;
  if (idx >= 0) {
    rssi = resp.substring(idx + 6).toInt();
  }
  if (rssi < 0 || rssi == 99) {
    Serial.println(F("   [FAIL] No signal reading (99 = unknown). Check antenna connection."));
  } else if (rssi < 10) {
    Serial.print(F("   [WARN] Weak signal, CSQ="));
    Serial.println(rssi);
  } else {
    Serial.print(F("   [PASS] CSQ="));
    Serial.println(rssi);
  }
  return rssi;
}

bool isRegistered() {
  Serial.println(F("\n[STEP] Network registration (CREG)"));
  sim800l.println(F("AT+CREG?"));
  String resp = readResponse(3000);

  int idx = resp.indexOf("+CREG:");
  if (idx < 0) {
    Serial.println(F("   [FAIL] No CREG response at all - check power/wiring."));
    return false;
  }
  // Look at the stat digit after the comma, e.g. "+CREG: 0,1"
  int comma = resp.indexOf(',', idx);
  int stat = -1;
  if (comma >= 0 && comma + 1 < (int)resp.length()) {
    stat = resp.substring(comma + 1, comma + 2).toInt();
  }

  switch (stat) {
    case 1:
      Serial.println(F("   [PASS] Registered, home network"));
      return true;
    case 5:
      Serial.println(F("   [PASS] Registered, roaming"));
      return true;
    case 0:
      Serial.println(F("   [FAIL] Not registered, not searching. Try AT+COPS=0."));
      return false;
    case 2:
      Serial.println(F("   [WAIT] Searching for network..."));
      return false;
    case 3:
      Serial.println(F("   [FAIL] Registration denied by network (check SIM balance/status)."));
      return false;
    default:
      Serial.println(F("   [FAIL] Unknown/garbled CREG status - possible power brownout during read."));
      return false;
  }
}

bool sendSMS(const char *phoneNumber, const char *message) {
  Serial.println(F("\n[STEP] Sending SMS"));

  if (!simSendAT("AT+CMGF=1")) {
    Serial.println(F("   [FAIL] Could not switch to text mode."));
    return false;
  }

  Serial.print(F(">> AT+CMGS=\""));
  Serial.print(phoneNumber);
  Serial.println(F("\""));
  sim800l.print(F("AT+CMGS=\""));
  sim800l.print(phoneNumber);
  sim800l.println(F("\""));

  if (!waitForPrompt(5000)) {
    Serial.println(F("   [FAIL] Never got '>' prompt - module busy or number format rejected. SMS body NOT sent."));
    return false;
  }

  sim800l.print(message);
  sim800l.write(26); // Ctrl+Z

  String resp = readResponse(15000);
  if (resp.indexOf("+CMGS:") >= 0) {
    Serial.println(F("   [PASS] SMS sent, network accepted it."));
    return true;
  }
  Serial.println(F("   [FAIL] No +CMGS confirmation - message may not have been delivered."));
  return false;
}

// ---------- Main ----------

void setup() {
  Serial.begin(115200);
  sim800l.begin(9600);
  delay(5000);

  Serial.println(F("\n===== SIM800L DIAGNOSTIC START ====="));

  if (!checkModuleAlive()) {
    Serial.println(F("\n>>> STOP: module not responding to AT at all."));
    Serial.println(F(">>> Check: TX/RX not swapped, common GND connected, baud rate 9600,"));
    Serial.println(F(">>> and that the module's power source can supply ~2A (not the Arduino 5V/3.3V pin)."));
    return;
  }

  simSendAT("ATE0");          // echo off
  simSendAT("AT+CMEE=1");     // verbose errors instead of bare "ERROR"

  if (!checkSimInserted()) {
    Serial.println(F("\n>>> STOP: fix SIM/PIN issue before continuing."));
    return;
  }

  simSendAT("AT+CCID");
  checkSignalQuality();
  isRegistered();
  simSendAT("AT+COPS?");

  Serial.println(F("\n[STEP] Requesting automatic network selection (can take up to 30s)"));
  simSendAT("AT+COPS=0", "OK", 30000);
}

void loop() {
  Serial.println(F("\n========== NETWORK CHECK =========="));

  int csq = checkSignalQuality();
  bool registered = isRegistered();

  if (registered) {
    if (!smsSent) {
      smsSent = sendSMS(SMS_PHONE_NUMBER, "SIM800L test message: module working.");
    }
  } else {
    Serial.println(F("\n>>> Still not registered."));
    if (csq < 0 || csq == 99) {
      Serial.println(F(">>> Signal is missing entirely - check antenna and power supply first."));
    } else {
      Serial.println(F(">>> Signal exists but no registration - check SIM balance/activation, or wait (2G search can take time)."));
    }
  }

  delay(30000);
}
