#include <Arduino.h>
#include <HX711.h>
#include <tunnel/socket.h>

HX711 loadcell;

// HX711 circuit wiring
const int LOADCELL_DOUT_PIN = 2;
const int LOADCELL_SCK_PIN = 16;

// Adjustment settings
const long LOADCELL_OFFSET = 0;
const long LOADCELL_DIVIDER = 1;

const int BLINK_LED_PIN = 0;

uint32_t loadcell_timer = 0;
const uint32_t loadcell_report_delay = 250;

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
    }
}

void setup()
{
    pinMode(BLINK_LED_PIN, OUTPUT);
    Serial.begin(115200);
    loadcell.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
    loadcell.set_scale(LOADCELL_DIVIDER);
    loadcell.set_offset(LOADCELL_OFFSET);

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
}

void loop()
{
    while (!tunnel::socket::check_connection()) {
        delay(1000);
    }
    packetCallback(tunnel::socket::readPacket());

    uint32_t current_time = millis();

    if (loadcell_timer > current_time) {
        loadcell_timer = current_time;
    }
    if (current_time - loadcell_timer > loadcell_report_delay)  {
        loadcell_timer = current_time;
        long weight = loadcell.read();
        tunnel::socket::writePacket("weight", "d", (int)weight);
    }
}
