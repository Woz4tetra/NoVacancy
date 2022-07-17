import socket

from lib.tunnel.protocol import TunnelProtocol

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.settimeout(2.0)

sock.bind(("0.0.0.0", 8080))
sock.listen(0)

protocol = TunnelProtocol(128, True)

buffer = b""

while True:
    client, addr = sock.accept()
    client.settimeout(1.0)
    while True:
        try:
            content = client.recv(1024)
            if len(content) == 0:
                break
        except socket.timeout:
            print("timeout")
            continue
        buffer += content
        remaining_buffer, buffer, results = protocol.parse_buffer(buffer)
        for result in results:
            if result.category == "weight":
                print("Weight:", result.get_int(4, signed=True))