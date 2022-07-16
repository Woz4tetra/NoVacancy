#include <Arduino.h>
#include <HX711.h>
#include <HCSR04.h>
#include <tunnel/socket.h>

HX711 loadcell;

#define BOARD_TYPE_BOOTH 0
#define BOARD_TYPE_DOOR 1
#define BOARD_TYPE_BIGSIGN 2

// #define BOARD_ID 0
// #define BOARD_TYPE BOARD_TYPE_BOOTH

#if BOARD_TYPE == BOARD_TYPE_BOOTH
// HX711 circuit wiring
const int LOADCELL_DOUT_PIN = 2;
const int LOADCELL_SCK_PIN = 16;

// Adjustment settings
const long LOADCELL_OFFSET = 0;
const long LOADCELL_DIVIDER = 1;

uint32_t report_timer = 0;
const uint32_t report_delay = 1000;

const int TRIGGER_PIN = 15;
const int ECHO_PIN = 16;  // TODO: assign different pin

HCSR04 ultrasonic(TRIGGER_PIN, ECHO_PIN);

#elif BOARD_TYPE == BOARD_TYPE_DOOR

#elif BOARD_TYPE == BOARD_TYPE_BIGSIGN

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
        if (!result->getDouble(value)) { return; }
        tunnel::socket::writePacket("ping", "e", value);
        Serial.println("Responding to ping");
    }
}

void setup()
{
    pinMode(BLINK_LED_PIN, OUTPUT);
    Serial.begin(115200);
    for (int count = 0; count < 10; count++)
    {
        digitalWrite(BLINK_LED_PIN, HIGH);
        delay(50);
        digitalWrite(BLINK_LED_PIN, LOW);
        delay(50);
    }
    if (!tunnel::socket::begin()) {
        while (!tunnel::socket::check_connection()) {
            delay(1000);
        }
    }

#if BOARD_TYPE == BOARD_TYPE_BOOTH
    loadcell.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
    loadcell.set_scale(LOADCELL_DIVIDER);
    loadcell.set_offset(LOADCELL_OFFSET);
#elif BOARD_TYPE == BOARD_TYPE_DOOR
#elif BOARD_TYPE == BOARD_TYPE_BIGSIGN
#endif
}

void loop()
{
    while (!tunnel::socket::check_connection()) {
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

        float distance = ultrasonic.dist();
        tunnel::socket::writePacket("dist", "f", distance);
        Serial.print("Sending distance: ");
        Serial.println(distance);
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
    }
}
