
#include "tunnel/socket.h"


namespace tunnel
{
namespace socket
{
WiFiClient client;

char* _read_buffer;
char* _write_buffer;
uint32_t start_wait_time;
bool _initialized = false;
TunnelProtocol* _protocol;
PacketResult* _result;

bool begin()
{
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    WiFi.mode(WIFI_STA);
    _protocol = new TunnelProtocol();
    _result = new PacketResult(TunnelProtocol::NULL_ERROR, 0);
    _read_buffer = new char[TunnelProtocol::MAX_PACKET_LEN];
    _write_buffer = new char[TunnelProtocol::MAX_PACKET_LEN];

    for (int index = 0; index < TunnelProtocol::MAX_PACKET_LEN; index++) {
        _read_buffer[index] = '\0';
    }

    while (WiFi.status() != WL_CONNECTED) {
        delay(250);
        DEBUG_SERIAL.print(".");
    }
    DEBUG_SERIAL.println("\nWiFi connected");  
    DEBUG_SERIAL.println("IP address: ");
    DEBUG_SERIAL.println(WiFi.localIP());

    DEBUG_SERIAL.print("connecting to ");
    DEBUG_SERIAL.print(WIFI_HOST);
    DEBUG_SERIAL.print(":");
    DEBUG_SERIAL.println(WIFI_PORT);
    
    // Use WiFiClient class to create TCP connections
    if (!client.connect(WIFI_HOST, WIFI_PORT)) {
        DEBUG_SERIAL.println("connection failed");
        return false;
    }
    _initialized = true;
    return true;
}

bool check_connection()
{
    if (client.connected()) {
        _initialized = true;
        return true;
    }
    DEBUG_SERIAL.println("attemping connection");
    _initialized = client.connect(WIFI_HOST, WIFI_PORT);
    if (_initialized) {
        DEBUG_SERIAL.println("connection succeeded!");
    }
    else {
        DEBUG_SERIAL.println("connection failed");
    }
    return _initialized;
}

PacketResult* readPacket()
{
    if (!client.available()) {
        return NULL;
    }
    if (!_initialized) {
        return NULL;
    }

    char c = client.read();
    if (c == TunnelProtocol::PACKET_START_0) {
       start_wait_time = millis();
        while (!client.available()) {
            if (millis() - start_wait_time > PACKET_STOP_TIMEOUT) {
                DEBUG_SERIAL.println(F("Time out exceeded for start"));
                return NULL;
            }
        }
        c = client.read();
        if (c != TunnelProtocol::PACKET_START_1) {
            return NULL;
        }
    }
    else {
        return NULL;
    }
    int _num_chars_read = 0;
    _read_buffer[_num_chars_read++] = TunnelProtocol::PACKET_START_0;
    _read_buffer[_num_chars_read++] = TunnelProtocol::PACKET_START_1;
    
    start_wait_time = millis();
    int packet_len = 0;
    while (true)
    {
        if (millis() - start_wait_time > PACKET_STOP_TIMEOUT) {
            DEBUG_SERIAL.println(F("Time out exceeded"));
            break;
        }
        if (!client.available()) {
            continue;
        }

        c = client.read();
        _read_buffer[_num_chars_read++] = c;
        if (_num_chars_read >= TunnelProtocol::MAX_PACKET_LEN) {
            DEBUG_SERIAL.println(F("Max num chars exceeded"));
            return NULL;
        }
        if (_num_chars_read == TunnelProtocol::CHECKSUM_START_INDEX) {
            packet_len = (int)to_uint16(_read_buffer + TunnelProtocol::LENGTH_START_INDEX);
        }
        else if (_num_chars_read > TunnelProtocol::CHECKSUM_START_INDEX) {
            if (packet_len >= TunnelProtocol::MAX_PACKET_LEN) {
                DEBUG_SERIAL.println(F("Max packet len exceeded"));
                return NULL;
            }
            if (_num_chars_read - TunnelProtocol::CHECKSUM_START_INDEX > packet_len)
            {
                if (c != TunnelProtocol::PACKET_STOP) {
                    DEBUG_SERIAL.print(F("_num_chars_read: "));
                    DEBUG_SERIAL.println(_num_chars_read);
                    DEBUG_SERIAL.println(F("Last char not stop"));
                    return NULL;
                }
                break;
            }
        }
    }
    _read_buffer[_num_chars_read] = '\0';

    _result->setErrorCode(TunnelProtocol::NULL_ERROR);
    _protocol->parsePacket(_read_buffer, 0, _num_chars_read, _result);
    int code = _result->getErrorCode();
    if (code == TunnelProtocol::NULL_ERROR) {
        return NULL;
    }
    if (_protocol->isCodeError(code)) {
        DEBUG_SERIAL.print(F("Encountered error code: "));
        DEBUG_SERIAL.println(code);
        return NULL;
    }
    if (_result->getPacketType() == PACKET_TYPE_HANDSHAKE) {
        writeConfirmingPacket(_result->getCategory().c_str(), "ud", _result->getPacketNum(), _result->getErrorCode());
    }
    return _result;
}

// TODO: add writeHandshakePacket

void writeConfirmingPacket(const char *category, const char *formats, ...)
{
    va_list args;
    va_start(args, formats);
    int length = _protocol->makePacket(PACKET_TYPE_CONFIRMING, _write_buffer, category, formats, args);
    writeBuffer(length);
    va_end(args);
}


void writePacket(const char *category, const char *formats, ...)
{
    va_list args;
    va_start(args, formats);
    int length = _protocol->makePacket(PACKET_TYPE_NORMAL, _write_buffer, category, formats, args);
    writeBuffer(length);
    va_end(args);
}

void writeBuffer(int length)
{
    if (!_initialized) {
        DEBUG_SERIAL.println(F("Device is not initialized. Skipping write"));
        return;
    }
    // REPORT_ERROR("Writing packet", packetToString(_write_buffer, 0, length).c_str());
    if (0 < length && length < TunnelProtocol::MAX_PACKET_LEN) {
        client.write(_write_buffer, length);
    }
    else {
        DEBUG_SERIAL.println(F("Skipping write for packet"));
    }
}

}
}