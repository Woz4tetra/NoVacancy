#pragma once

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "tunnel/protocol.h"


const uint32_t PACKET_STOP_TIMEOUT = 500;

#ifndef DEBUG_SERIAL
#define DEBUG_SERIAL Serial
#endif

namespace tunnel
{
namespace socket
{
bool begin();
bool check_connection();
PacketResult* readPacket();
void writePacket(const char *category, const char *formats, ...);
void writeConfirmingPacket(const char *category, const char *formats, ...);
void writeBuffer(int length);
}
}
