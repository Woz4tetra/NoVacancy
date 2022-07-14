#pragma once

#include <Arduino.h>
#include "tunnel/protocol.h"

#define PROTOCOL_SERIAL Serial
#define PROTOCOL_BAUD 1000000

#ifndef DEBUG_SERIAL
#define DEBUG_SERIAL PROTOCOL_SERIAL
#endif


const uint32_t PACKET_STOP_TIMEOUT = 500;

namespace tunnel
{
namespace serial
{
bool begin();
PacketResult* readPacket();
void writePacket(const char *category, const char *formats, ...);
void writeConfirmingPacket(const char *category, const char *formats, ...);
void writeBuffer(int length);
}
}
