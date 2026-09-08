
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <ILI9488.h>

#define TFT_CS_PIN  53
#define TFT_DC_PIN  49
#define TFT_RST_PIN 8

// Hardware SPI: MOSI 51, MISO 50, SCK 52 (fixed pins on the Mega, used automatically)
ILI9488 tft = ILI9488(TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);

void setup() {
  Serial.begin(9600);
  Serial.println("ILI9488 test starting...");

  tft.begin();
  tft.setRotation(1);           // 0-3, rotate if text looks sideways/upside down
  tft.fillScreen(ILI9488_BLACK);

  tft.setCursor(20, 20);
  tft.setTextColor(ILI9488_WHITE);
  tft.setTextSize(4);
  tft.println("hello reda");

  Serial.println("Done. Check the screen.");
}

void loop() {
  // nothing here
}
