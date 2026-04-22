#include <WebServer.h>
#include "website.h"
#include <WiFi.h>
#include <Arduino.h>
#include <ESP32Servo.h>
#include <Preferences.h>
#include <Adafruit_MLX90640.h>
// Pin Definitions
#define MQ2_PIN 34
#define PUMP_PIN 26
#define BUZZER_PIN 4
#define SERVO_X_PIN 18
#define SERVO_Y_PIN 19
#define SERVO_DOOR_PIN 25

// Thresholds
#define FIRE_TEMP_THRESHOLD 50.0
#define SMOKE_ADC_THRESHOLD 2000

// PID Control Constants
#define PID_KP 0.30f
#define PID_KI 0.05f
#define PID_KD 0.15f

// Thermal Stability
#define THERMAL_EMA_ALPHA 0.40f // Lower = smoother but slower (0.0 to 1.0)
#define FIRE_HYSTERESIS 2.5f

// Servo Settings
#define SERVO_DEADBAND 1
#define SERVO_HOME_X 90
#define SERVO_HOME_Y 90
#define SERVO_X_MIN 0
#define SERVO_X_MAX 180
#define SERVO_Y_MIN 40
#define SERVO_Y_MAX 140

#define DOOR_CLOSED 90
#define DOOR_OPEN 0

#define DEBUG_INTERVAL_MS 1000


const char* WIFI_SSID = "FireSystem";
const char* WIFI_PASS = "12345678";

// Hardware Objects
Adafruit_MLX90640 mlx;
WebServer server(80);
Servo servoX;
Servo servoY;
Servo servoDoor;

// Task Handles
TaskHandle_t sensorHandle;

// Control Variables
float smoothX = SERVO_HOME_X;
float smoothY = SERVO_HOME_Y;
float errorTargetX = 0, errorTargetY = 0;
float integralX = 0, integralY = 0;
float lastErrorX = 0, lastErrorY = 0;

int lastWrittenX = -1;
int lastWrittenY = -1;
unsigned long lastDebugMs = 0;
bool cameraOK = false;

// Multi-frame averaging buffer (EMA)
float emaFrame[768];
// Shared System State
struct SystemState {
    float frame[768];
    float maxTemp;
    int maxIndex;
    int gasValue;
    bool fireDetected;
    bool smokeDetected;
    bool pumpOn;
    bool doorOpen;
    bool manualMode;
    int servoX;
    int servoY;
    int manualTargetX;
    int manualTargetY;
    int customHomeX;
    int customHomeY;
    bool fireActive; 
};

// Define Global State
SystemState state;
SemaphoreHandle_t dataMutex;
Preferences prefs;


void setup() {
  Serial.begin(9600);
  delay(1000); 
  Serial.println(F("\n--- Localized Fire System v6.0 ---"));

  system_data_init();

  // Hardware Setup
  servos_setup();
  buzzer_setup();
  pump_setup();
  gas_sensor_setup();
  
  smoothX = state.customHomeX;
  smoothY = state.customHomeY;

  // Camera Setup
  cameraOK = camera_setup();
  
  // Initialize EMA frame with ambient
  for(int i=0; i<768; i++) emaFrame[i] = 25.0;

  start_wifi();
  server_setup();
  multitasking_starts();

  Serial.println(F("[ROOT] PID & Thermal Averaging Online.\n"));
}

void pump_setup() {
    pinMode(PUMP_PIN, OUTPUT);
    digitalWrite(PUMP_PIN, LOW);
}

void system_data_init() {
    // 1. Create Mutex
    dataMutex = xSemaphoreCreateMutex();
    if (dataMutex == NULL) {
        Serial.println(F("[FATAL] Mutex failed!"));
        while (1) delay(1000);
    }
    Serial.println(F("[INIT] Mutex created"));

    // 2. Load Preferences
    prefs.begin("fire-system", false);
    state.customHomeX = prefs.getInt("homeX", SERVO_HOME_X);
    state.customHomeY = prefs.getInt("homeY", SERVO_HOME_Y);
    
    // Constraints check (in case garbage was in flash)
    state.customHomeX = constrain(state.customHomeX, SERVO_X_MIN, SERVO_X_MAX);
    state.customHomeY = constrain(state.customHomeY, SERVO_Y_MIN, SERVO_Y_MAX);
    
    state.manualTargetX = state.customHomeX;
    state.manualTargetY = state.customHomeY;
    
    Serial.printf("[INIT] Persistent Home loaded: X=%d Y=%d\n", state.customHomeX, state.customHomeY);
}

void buzzer_setup() {
    pinMode(BUZZER_PIN, OUTPUT);
    noTone(BUZZER_PIN);
}

void setDoor(bool open) {
    if (open) {
        servoDoor.write(DOOR_OPEN);
    } else {
        servoDoor.write(DOOR_CLOSED);
    }
    if (xSemaphoreTake(dataMutex, pdMS_TO_TICKS(10))) {
        state.doorOpen = open;
        xSemaphoreGive(dataMutex);
    }
}


void setBuzzer(bool on) {
    if (on) {
        tone(BUZZER_PIN, 2000);
    } else {
        noTone(BUZZER_PIN);
    }
}


void setPump(bool on) {
    digitalWrite(PUMP_PIN, on ? HIGH : LOW);
    if (xSemaphoreTake(dataMutex, pdMS_TO_TICKS(10))) {
        state.pumpOn = on;
        xSemaphoreGive(dataMutex);
    }
}

void loop() {
  server.handleClient();
  vTaskDelay(pdMS_TO_TICKS(5));
}

void multitasking_starts() {
    xTaskCreatePinnedToCore(
        sensorTask,
        "SensorTask",
        8192,
        NULL,
        1,
        &sensorHandle,
        1);
    
    Serial.println(F("[INIT] Sensor Task launched — Core 1"));
}


void servos_setup() {
  servoX.attach(SERVO_X_PIN);
  servoY.attach(SERVO_Y_PIN);
  servoDoor.attach(SERVO_DOOR_PIN);

  // Initial positions
  servoX.write(SERVO_HOME_X);
  servoY.write(SERVO_HOME_Y);
  servoDoor.write(DOOR_CLOSED);

  if (xSemaphoreTake(dataMutex, portMAX_DELAY)) {
    state.servoX = SERVO_HOME_X;
    state.servoY = SERVO_HOME_Y;
    state.doorOpen = false;
    state.customHomeX = SERVO_HOME_X;
    state.customHomeY = SERVO_HOME_Y;
    state.manualTargetX = SERVO_HOME_X;
    state.manualTargetY = SERVO_HOME_Y;
    xSemaphoreGive(dataMutex);
  }
}


bool camera_setup() {
  Wire.begin(21, 22);
  Wire.setClock(400000);
  Serial.print(F("[INIT] MLX90640... "));
  if (!mlx.begin()) {
    Serial.println(F("NOT FOUND! Check SDA(21)/SCL(22)."));
    return false;
  } else {
    mlx.setRefreshRate(MLX90640_4_HZ);
    Serial.println(F("OK — 4 Hz"));
    return true;
  }
}

void findMaxTemp() {
  if (xSemaphoreTake(dataMutex, pdMS_TO_TICKS(5))) {
    state.maxTemp = state.frame[0];
    state.maxIndex = 0;
    for (int i = 1; i < 768; i++) {
      if (state.frame[i] > state.maxTemp) {
        state.maxTemp = state.frame[i];
        state.maxIndex = i;
      }
    }
    xSemaphoreGive(dataMutex);
  }
}

void gas_sensor_setup() {
  pinMode(MQ2_PIN, INPUT);
}

void updateGasReading() {
  int val = analogRead(MQ2_PIN);
  if (xSemaphoreTake(dataMutex, pdMS_TO_TICKS(10))) {
    state.gasValue = val;
    state.smokeDetected = (val > SMOKE_ADC_THRESHOLD);
    xSemaphoreGive(dataMutex);
  }
}

void sensorTask(void* pvParameters) {
  while (true) {
    // 1. Industrial-Level Thermal Averaging (EMA)
    float rawFrame[768];
    if (cameraOK && mlx.getFrame(rawFrame) == 0) {
      if (xSemaphoreTake(dataMutex, pdMS_TO_TICKS(10))) {
        for (int i = 0; i < 768; i++) {
          emaFrame[i] = (emaFrame[i] * (1.0f - THERMAL_EMA_ALPHA)) + (rawFrame[i] * THERMAL_EMA_ALPHA);
          state.frame[i] = emaFrame[i];
        }
        findMaxTemp(); // Finds max on averaged data
        xSemaphoreGive(dataMutex);
      }
    }

    updateGasReading();

    if (xSemaphoreTake(dataMutex, pdMS_TO_TICKS(10))) {
      // Logic
      if (!state.fireDetected) {
        state.fireDetected = (state.maxTemp >= FIRE_TEMP_THRESHOLD);
      } else {
        state.fireDetected = (state.maxTemp >= (FIRE_TEMP_THRESHOLD - FIRE_HYSTERESIS));
      }

      bool alarmActive = state.fireDetected || state.smokeDetected;
      setBuzzer(alarmActive);

      if (alarmActive && !state.doorOpen) setDoor(true);
      else if (!alarmActive && state.doorOpen) setDoor(false);

      if (state.fireDetected) {
        if (!state.pumpOn) setPump(true);
        state.fireActive = true;
        state.manualMode = false;

        // Target from Thermal Data
        int px = state.maxIndex % 32;
        int py = state.maxIndex / 32;
        float targetX = map(px, 0, 31, SERVO_X_MIN, SERVO_X_MAX);
        float targetY = map(py, 0, 23, SERVO_Y_MIN, SERVO_Y_MAX);

        // 2. Fire Tracking PID Controller
        float errorX = targetX - smoothX;
        float errorY = targetY - smoothY;

        integralX += errorX;
        integralY += errorY;
        integralX = constrain(integralX, -50, 50); // Anti-windup
        integralY = constrain(integralY, -50, 50);

        float derivativeX = errorX - lastErrorX;
        float derivativeY = errorY - lastErrorY;

        float outputX = (errorX * PID_KP) + (integralX * PID_KI) + (derivativeX * PID_KD);
        float outputY = (errorY * PID_KP) + (integralY * PID_KI) + (derivativeY * PID_KD);

        smoothX += outputX;
        smoothY += outputY;

        lastErrorX = errorX;
        lastErrorY = errorY;
      } else {
        if (state.pumpOn) setPump(false);
        if (state.fireActive) {
          state.manualTargetX = state.customHomeX;
          state.manualTargetY = state.customHomeY;
          state.fireActive = false;
          integralX = 0; integralY = 0; // Reset PID
        }

        if (state.manualMode) {
          smoothX += (state.manualTargetX - smoothX) * 0.2f;
          smoothY += (state.manualTargetY - smoothY) * 0.2f;
        } else {
          smoothX += (state.customHomeX - smoothX) * 0.1f;
          smoothY += (state.customHomeY - smoothY) * 0.1f;
        }
      }

      // Output
      int rx = constrain((int)round(smoothX), SERVO_X_MIN, SERVO_X_MAX);
      int ry = constrain((int)round(smoothY), SERVO_Y_MIN, SERVO_Y_MAX);

      if (abs(rx - lastWrittenX) >= SERVO_DEADBAND) {
        servoX.write(rx);
        state.servoX = lastWrittenX = rx;
      }
      if (abs(ry - lastWrittenY) >= SERVO_DEADBAND) {
        servoY.write(ry);
        state.servoY = lastWrittenY = ry;
      }

      xSemaphoreGive(dataMutex);
    }

    debugPrint();
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

void debugPrint() {
  unsigned long now = millis();
  if (now - lastDebugMs < DEBUG_INTERVAL_MS) return;
  lastDebugMs = now;
  if (xSemaphoreTake(dataMutex, pdMS_TO_TICKS(5))) {
    Serial.printf("[DEBUG] T:%.1f Fire:%d Servo:[%d, %d]\n", state.maxTemp, state.fireDetected, state.servoX, state.servoY);
    xSemaphoreGive(dataMutex);
  }
}

void server_setup() {
    server.on("/", HTTP_GET, []() {
        Serial.println(F("[HTTP] Root page requested"));
        server.sendHeader("Content-Type", "text/html; charset=UTF-8");
        server.send_P(200, "text/html", INDEX_HTML);
    });

    server.on("/data", HTTP_GET, []() {
        // Serial.println(F("[HTTP] Data poll")); // Optional: very spammy, keeping it off for now
        server.sendHeader("Access-Control-Allow-Origin", "*");
        String j;
        j.reserve(256);
        if (xSemaphoreTake(dataMutex, pdMS_TO_TICKS(100))) {
            j = F("{\"maxTemp\":");
            j += String(state.maxTemp, 1);
            j += F(",\"fire\":");
            j += state.fireDetected ? F("true") : F("false");
            j += F(",\"smoke\":");
            j += state.smokeDetected ? F("true") : F("false");
            j += F(",\"pumpOn\":");
            j += state.pumpOn ? F("true") : F("false");
            j += F(",\"gasRaw\":");
            j += state.gasValue;
            j += F(",\"servoX\":");
            j += state.servoX;
            j += F(",\"servoY\":");
            j += state.servoY;
            j += F(",\"threshold\":");
            j += String(FIRE_TEMP_THRESHOLD, 0);
            j += F(",\"uptime\":");
            j += millis() / 1000;
            j += F(",\"doorOpen\":");
            j += state.doorOpen ? F("true") : F("false");
            j += F(",\"homeX\":");
            j += state.customHomeX;
            j += F(",\"homeY\":");
            j += state.customHomeY;
            j += F("}");
            xSemaphoreGive(dataMutex);
        } else {
            j = F("{\"error\":\"busy\"}");
        }
        server.send(200, "application/json", j);
    });

    server.on("/frame", HTTP_GET, []() {
        server.sendHeader("Access-Control-Allow-Origin", "*");
        String j;
        j.reserve(768 * 6);
        j = "[";
        if (xSemaphoreTake(dataMutex, pdMS_TO_TICKS(200))) {
            for (int i = 0; i < 768; i++) {
                j += String(state.frame[i], 1);
                if (i < 767) j += ",";
            }
            xSemaphoreGive(dataMutex);
        } else {
            server.send(503, "application/json", "[]");
            return;
        }
        j += "]";
        server.send(200, "application/json", j);
    });

    server.on("/move", HTTP_GET, []() {
        server.sendHeader("Access-Control-Allow-Origin", "*");
        String dir = server.arg("dir");
        if (xSemaphoreTake(dataMutex, pdMS_TO_TICKS(50))) {
            Serial.printf("[HTTP] Move request: %s\n", dir.c_str());
            if (dir == "left") state.manualTargetX = constrain(state.manualTargetX - 10, SERVO_X_MIN, SERVO_X_MAX);
            else if (dir == "right") state.manualTargetX = constrain(state.manualTargetX + 10, SERVO_X_MIN, SERVO_X_MAX);
            else if (dir == "up") state.manualTargetY = constrain(state.manualTargetY - 10, SERVO_Y_MIN, SERVO_Y_MAX);
            else if (dir == "down") state.manualTargetY = constrain(state.manualTargetY + 10, SERVO_Y_MIN, SERVO_Y_MAX);
            else if (dir == "home") {
                state.manualTargetX = state.customHomeX;
                state.manualTargetY = state.customHomeY;
                Serial.printf("[MANUAL] Returning to Home: X=%d Y=%d\n", state.customHomeX, state.customHomeY);
            } else if (dir == "sethome") {
                state.customHomeX = state.manualTargetX;
                state.customHomeY = state.manualTargetY;
                prefs.putInt("homeX", state.customHomeX);
                prefs.putInt("homeY", state.customHomeY);
                Serial.printf("[MANUAL] Home saved to Flash: X=%d Y=%d\n", state.customHomeX, state.customHomeY);
            }
            state.manualMode = true;
            xSemaphoreGive(dataMutex);
        } else {
            Serial.println(F("[HTTP] Move failed - Mutex busy"));
        }
        server.send(200, "text/plain", "OK");
    });

    server.begin();
    Serial.println(F("[INIT] HTTP server started"));
}

void start_wifi() {
  WiFi.softAP(WIFI_SSID, WIFI_PASS);
  Serial.print(F("[INIT] WiFi AP: "));
  Serial.print(WIFI_SSID);
  Serial.print(F(" IP: "));
  Serial.println(WiFi.softAPIP());
}
