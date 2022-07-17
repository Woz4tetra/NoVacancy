#include <Arduino.h>
#include <tunnel/socket.h>

#define BOARD_TYPE_BOOTH 0
#define BOARD_TYPE_DOOR 1
#define BOARD_TYPE_BIGSIGN 2

// #define USE_ULTRASONIC

// #define BOARD_ID 0
// #define BOARD_TYPE BOARD_TYPE_BOOTH

#if BOARD_TYPE == BOARD_TYPE_BOOTH
#include <HX711.h>
#include <Adafruit_NeoPixel.h>
#ifdef __AVR__
#include <avr/power.h> // Required for 16 MHz Adafruit Trinket
#endif
#ifdef USE_ULTRASONIC
#include <HCSR04.h>
#endif

// HX711 circuit wiring
const int LOADCELL_DOUT_PIN = 2;
const int LOADCELL_SCK_PIN = 16;

HX711 loadcell;

// Adjustment settings
const long LOADCELL_OFFSET = 0;
const long LOADCELL_DIVIDER = 1;

uint32_t report_timer = 0;
const uint32_t report_delay = 1000;

const int LED_PIN = 14;
const int LED_COUNT = 56;

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
// Argument 1 = Number of pixels in NeoPixel strip
// Argument 2 = Arduino pin number (most are valid)
// Argument 3 = Pixel type flags, add together as needed:
//   NEO_KHZ800  800 KHz bitstream (most NeoPixel products w/WS2812 LEDs)
//   NEO_KHZ400  400 KHz (classic 'v1' (not v2) FLORA pixels, WS2811 drivers)
//   NEO_GRB     Pixels are wired for GRB bitstream (most NeoPixel products)
//   NEO_RGB     Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
//   NEO_RGBW    Pixels are wired for RGBW bitstream (NeoPixel RGBW products)

uint32_t VACANT_COLOR = strip.Color(0, 255, 0);
uint32_t OCCUPIED_COLOR = strip.Color(255, 0, 0);
uint32_t IDLE_COLOR = strip.Color(255, 255, 0);

#ifdef USE_ULTRASONIC
const int TRIGGER_PIN = 15;  // TODO: assign different pin
const int ECHO_PIN = 16;  // TODO: assign different pin
HCSR04 ultrasonic(TRIGGER_PIN, ECHO_PIN);
#endif

void setColor(uint32_t color)
{
    for(int i = 0; i < strip.numPixels(); i++) {
        strip.setPixelColor(i, color);
    }
    strip.show();
}

void wipeMiddle(uint32_t color)
{
    int forward, reverse;
    int middle = strip.numPixels() / 2;
    for(int i = 0; i < middle + 1; i++) {
        forward = middle + i;
        reverse = middle - i;
        strip.setPixelColor(forward, color);
        strip.setPixelColor(reverse, color);
        delay(5);
        strip.show();
    }
}

#elif BOARD_TYPE == BOARD_TYPE_DOOR

#elif BOARD_TYPE == BOARD_TYPE_BIGSIGN

#include <SPI.h>
#include <SD.h>
#include <Adafruit_VS1053.h>


// These are the pins used
#define VS1053_RESET   -1     // VS1053 reset pin (not used!)

// Feather ESP8266
#if defined(ESP8266)
  #define VS1053_CS      16     // VS1053 chip select pin (output)
  #define VS1053_DCS     15     // VS1053 Data/command select pin (output)
  #define CARDCS          2     // Card chip select pin
  #define VS1053_DREQ     0     // VS1053 Data request, ideally an Interrupt pin

// Feather ESP32
#elif defined(ESP32) && !defined(ARDUINO_ADAFRUIT_FEATHER_ESP32S2)
  #define VS1053_CS      32     // VS1053 chip select pin (output)
  #define VS1053_DCS     33     // VS1053 Data/command select pin (output)
  #define CARDCS         14     // Card chip select pin
  #define VS1053_DREQ    15     // VS1053 Data request, ideally an Interrupt pin

// Feather Teensy3
#elif defined(TEENSYDUINO)
  #define VS1053_CS       3     // VS1053 chip select pin (output)
  #define VS1053_DCS     10     // VS1053 Data/command select pin (output)
  #define CARDCS          8     // Card chip select pin
  #define VS1053_DREQ     4     // VS1053 Data request, ideally an Interrupt pin

// WICED feather
#elif defined(ARDUINO_STM32_FEATHER)
  #define VS1053_CS       PC7     // VS1053 chip select pin (output)
  #define VS1053_DCS      PB4     // VS1053 Data/command select pin (output)
  #define CARDCS          PC5     // Card chip select pin
  #define VS1053_DREQ     PA15    // VS1053 Data request, ideally an Interrupt pin

#elif defined(ARDUINO_NRF52832_FEATHER )
  #define VS1053_CS       30     // VS1053 chip select pin (output)
  #define VS1053_DCS      11     // VS1053 Data/command select pin (output)
  #define CARDCS          27     // Card chip select pin
  #define VS1053_DREQ     31     // VS1053 Data request, ideally an Interrupt pin

// Feather M4, M0, 328, ESP32S2, nRF52840 or 32u4
#else
  #define VS1053_CS       6     // VS1053 chip select pin (output)
  #define VS1053_DCS     10     // VS1053 Data/command select pin (output)
  #define CARDCS          5     // Card chip select pin
  // DREQ should be an Int pin *if possible* (not possible on 32u4)
  #define VS1053_DREQ     9     // VS1053 Data request, ideally an Interrupt pin

#endif

Adafruit_VS1053_FilePlayer music_player = 
  Adafruit_VS1053_FilePlayer(VS1053_RESET, VS1053_CS, VS1053_DCS, VS1053_DREQ, CARDCS);

// relay pin for toggling 'NO' sign
const int RELAY_PIN = 14;

bool player_initialized = false;


/// File listing helper
void printDirectory(File dir, int numTabs) {
   while(true) {
     
     File entry =  dir.openNextFile();
     if (! entry) {
       // no more files
       //Serial.println("**nomorefiles**");
       break;
     }
     for (uint8_t i=0; i<numTabs; i++) {
       Serial.print('\t');
     }
     Serial.print(entry.name());
     if (entry.isDirectory()) {
       Serial.println("/");
       printDirectory(entry, numTabs+1);
     } else {
       // files have sizes, directories do not
       Serial.print("\t\t");
       Serial.println(entry.size(), DEC);
     }
     entry.close();
   }
}

void setBigSignVacant() {
    Serial.println("Runnning vacancy sequence");
    digitalWrite(RELAY_PIN, LOW);
    delay(250);
    if (player_initialized) {
        // music_player.playFullFile("/neon_sign_1.mp3");
        music_player.playFullFile("/track001.mp3");
        delay(2000);
        music_player.stopPlaying();
    }
    else {
        Serial.println("Player isn't initialized. Can't play sound");
    }
}


void setBigSignOccupied() {
    Serial.println("Runnning occupied sequence");
    digitalWrite(RELAY_PIN, HIGH);
    delay(250);
    if (player_initialized) {
        // music_player.playFullFile("/neon_sign_2.mp3");
        music_player.playFullFile("/track001.mp3");
    }
    else {
        Serial.println("Player isn't initialized. Can't play sound");
    }
}

#else
#error Invalid board type defined

#endif
 

const int BLINK_LED_PIN = 0;

uint32_t heartbeat_timer = 0;
const uint32_t heartbeat_delay = 1000;

void packetCallback(PacketResult* result)
{
    // if the result is not set for some reason, don't do anything
    if (result == NULL) {
        return;
    }

    // Extract category and check which event it maps to
    String category = result->getCategory();
    if (category.equals("ping")) {
        // Respond to ping by writing back the same value
        double value;
        if (!result->getDouble(value)) { Serial.println("Failed to get ping value"); return; }
        tunnel::socket::writePacket("ping", "e", value);
        tunnel::socket::update_ping();
        Serial.println("Responding to ping");
    }
#if BOARD_TYPE == BOARD_TYPE_BOOTH
    else if (category.equals("led")) {
        String pattern;
        if (!result->getString(pattern)) { Serial.println("Failed to get pattern value"); return; }
        if (pattern.equals("occupied")) {
            wipeMiddle(OCCUPIED_COLOR);
        }
        else if (pattern.equals("vacant")) {
            wipeMiddle(VACANT_COLOR);
        }
    }
#elif BOARD_TYPE == BOARD_TYPE_DOOR
#elif BOARD_TYPE == BOARD_TYPE_BIGSIGN
    else if (category.equals("bigsign")) {
        bool state;
        if (!result->getBool(state)) { Serial.println("Failed to get big sign state"); return; }
        if (state) {
            setBigSignOccupied();
        }
        else {
            setBigSignVacant();
        }
    }
    else if (category.equals("volume")) {
        uint8_t volume;
        if (!result->getUInt8(volume)) { Serial.println("Failed to get volume"); return; }
        music_player.setVolume(volume, volume);
    }
#endif

}

void flash_builtin_led(int flashes)
{
    for (int count = 0; count < flashes; count++)
    {
        digitalWrite(BLINK_LED_PIN, HIGH);
        delay(50);
        digitalWrite(BLINK_LED_PIN, LOW);
        delay(50);
    }
    digitalWrite(BLINK_LED_PIN, HIGH);
}

void setup()
{
    pinMode(BLINK_LED_PIN, OUTPUT);
    Serial.begin(115200);
    flash_builtin_led(10);

#if BOARD_TYPE == BOARD_TYPE_BOOTH
    loadcell.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
    loadcell.set_scale(LOADCELL_DIVIDER);
    loadcell.set_offset(LOADCELL_OFFSET);

#if defined(__AVR_ATtiny85__) && (F_CPU == 16000000)
    clock_prescale_set(clock_div_1);
#endif
    strip.begin();           // INITIALIZE NeoPixel strip object (REQUIRED)
    strip.show();            // Turn OFF all pixels ASAP
    setColor(IDLE_COLOR);
#elif BOARD_TYPE == BOARD_TYPE_DOOR
#elif BOARD_TYPE == BOARD_TYPE_BIGSIGN
    pinMode(RELAY_PIN, OUTPUT);

    if (music_player.begin()) {
        music_player.sineTest(0x44, 500);    // Make a tone to indicate VS1053 is working

        if (SD.begin(CARDCS)) {
            // Set volume for left, right channels. lower numbers == louder volume!
            music_player.setVolume(10, 10);

#if defined(__AVR_ATmega32U4__) 
            // Timer interrupts are not suggested, better to use DREQ interrupt!
            // but we don't have them on the 32u4 feather...
            music_player.useInterrupt(VS1053_FILEPLAYER_TIMER0_INT); // timer int
#else
            // If DREQ is on an interrupt pin we can do background
            // audio playing
            music_player.useInterrupt(VS1053_FILEPLAYER_PIN_INT);  // DREQ int
#endif
        }
        else {
            Serial.println(F("SD failed, or not present"));
        }
    }
    else {
        Serial.println(F("Couldn't find VS1053, do you have the right pins defined?"));
    }
    player_initialized = true;

    for (int count = 0; count < 3; count++)
    {
        digitalWrite(RELAY_PIN, LOW);
        delay(500);
        digitalWrite(RELAY_PIN, HIGH);
        delay(500);
    }
    digitalWrite(RELAY_PIN, LOW);

#endif

    if (!tunnel::socket::begin()) {
        while (!tunnel::socket::check_connection()) {
        flash_builtin_led(3);
            delay(1000);
        }
    }
}

void loop()
{
    while (!tunnel::socket::check_connection()) {
        flash_builtin_led(3);
#if BOARD_TYPE == BOARD_TYPE_BOOTH
        setColor(IDLE_COLOR);
#endif
        delay(1000);
    }
    packetCallback(tunnel::socket::readPacket());

    uint32_t current_time = millis();

#if BOARD_TYPE == BOARD_TYPE_BOOTH
    if (report_timer > current_time) {
        report_timer = current_time;
    }
    if (current_time - report_timer > report_delay)  {
        report_timer = current_time;
        long weight = loadcell.read();
        tunnel::socket::writePacket("weight", "d", (int)weight);
        Serial.print("Sending weight: ");
        Serial.println(weight);

#ifdef USE_ULTRASONIC
        float distance = ultrasonic.dist();
        tunnel::socket::writePacket("dist", "f", distance);
        Serial.print("Sending distance: ");
        Serial.println(distance);
#endif
    }
#elif BOARD_TYPE == BOARD_TYPE_DOOR
#elif BOARD_TYPE == BOARD_TYPE_BIGSIGN
#endif

    if (heartbeat_timer > current_time) {
        heartbeat_timer = current_time;
    }
    if (current_time - heartbeat_timer > heartbeat_delay)  {
        heartbeat_timer = current_time;
        tunnel::socket::writePacket("heart", "uuu", BOARD_ID, BOARD_TYPE, current_time);
        Serial.print("Sending heartbeat: ");
        Serial.print(BOARD_ID);
        Serial.print(' ');
        Serial.println(BOARD_TYPE);
    }
}
