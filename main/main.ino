#include <Adafruit_NeoPixel.h>
#ifdef __AVR__
  #include <avr/power.h>
#endif

#define PIN 6
#define LED_COUNT 50

// originally based on Adafruit's strandtest example:
//   https://github.com/adafruit/Adafruit_NeoPixel/blob/312693bfce447095ff0d8b6f6a1cc569415d77d7/examples/strandtest/strandtest.ino
// relies on libraries from the same repo

Adafruit_NeoPixel strip = Adafruit_NeoPixel(LED_COUNT, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'
}

void loop() {
//  colorWipe(strip.Color(255, 0, 0), 50); // Red
//  colorWipe(strip.Color(0, 255, 0), 50); // Green

//  christmasChase(200, 10);

  colorWipe(strip.Color(0, 100, 0), 50); // Green
  dullWipe(strip.Color(255, 0, 0), strip.Color(0, 100, 0), 10, 3, 30); // Red on green
  colorWipe(strip.Color(100, 0, 0), 50); // Red
  dullWipe(strip.Color(0, 255, 0), strip.Color(100, 0, 0), 10, 3, 30); // Green on red

  rainbow(20);
}


void colorWipe(uint32_t c, uint8_t wait) {
  for(uint16_t i=0; i<strip.numPixels(); i++) {
    strip.setPixelColor(i, c);
    strip.show();
    delay(wait);
  }
}

// Slightly different, this makes the rainbow equally distributed throughout
void rainbow(uint8_t wait) {
  uint16_t i, j;

  for(j=0; j<256*5; j++) { // 5 cycles of all colors on wheel
    for(i=0; i< strip.numPixels(); i++) {
      strip.setPixelColor(i, Wheel(((i * 256 / strip.numPixels()) + j) & 255));
    }
    strip.show();
    delay(wait);
  }
}


void christmasChase(uint8_t wait, int cycleCount) {
  uint32_t red = strip.Color(255, 0, 0);
  uint32_t green = strip.Color(0, 255, 0);
  for (int j=0; j<cycleCount; j++) {  //do 10 cycles of chasing
    for (int q=0; q < 3; q++) {
      for (uint16_t i=0; i < strip.numPixels(); i=i+3) {
        strip.setPixelColor(i+q, red);    //turn every third pixel on
      }
      strip.show();

      delay(wait);

      for (uint16_t i=0; i < strip.numPixels(); i=i+3) {
        strip.setPixelColor(i+q, green);        //turn every third pixel off
      }
    }
  }
}

void dullWipe(uint32_t fgColor, uint32_t bgColor, int cycles, int width, int wait){
  for(int i=0; i < cycles; i++){
    int fgPixel=(0 - (width - 1));
    for(; fgPixel < strip.numPixels() || fgPixel < 0; fgPixel++){
      for(int p=0; p<strip.numPixels(); p++){
        if(p >= fgPixel && p <= (fgPixel + width)){
          strip.setPixelColor(p, fgColor);
        } else {
          strip.setPixelColor(p, bgColor);
        }
      }
      strip.show();
      delay(wait);
    }
  }
}


// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}

