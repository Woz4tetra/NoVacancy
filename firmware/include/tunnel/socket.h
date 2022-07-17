#pragma once

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "tunnel/protocol.h"


// #define WIFI_SSID 
// #define WIFI_PASSWORD 

// #define WIFI_HOST "10.35.11.4"
// #define WIFI_PORT 8080


#ifndef DEBUG_SERIAL
#define DEBUG_SERIAL Serial
#endif

namespace tunnel
{
namespace socket
{

const uint32_t PACKET_STOP_TIMEOUT = 500;
const uint32_t PING_TIMEOUT = 10000;

bool begin();
bool check_connection();
PacketResult* readPacket();
void writePacket(const char *category, const char *formats, ...);
void writeConfirmingPacket(const char *category, const char *formats, ...);
void writeBuffer(int length);
void update_ping();
}
}
