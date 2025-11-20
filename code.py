#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// OLED display size
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

// I2C address (usually 0x3C)
#define OLED_ADDR 0x3C

// Create display object
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

void setup() {
  Serial.begin(9600);

  // Initialize OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("SSD1306 allocation failed");
    for (;;);
  }

  display.clearDisplay();

  // Test 1: Draw text
  display.setTextSize(2);              // Text size
  display.setTextColor(SSD1306_WHITE); // Text color
  display.setCursor(0, 0);             // Start at top-left
  display.println("Hello!");
  display.display();
  delay(2000);

  // Test 2: Draw shapes
  display.clearDisplay();
  display.drawRect(10, 10, 50, 30, SSD1306_WHITE);  // rectangle
  display.fillCircle(80, 30, 10, SSD1306_WHITE);    // circle
  display.display();
  delay(2000);

  // Test 3: Scrolling text
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("Scrolling text demo");
  display.display();
  display.startscrollright(0x00, 0x0F);
  delay(3000);
  display.stopscroll();
}

void loop() {
  // Blink a message every second
  display.clearDisplay();
  display.setTextSize(2);
  display.setCursor(10, 20);
  display.println("Nano OLED!");
  display.display();
  delay(1000);
}
