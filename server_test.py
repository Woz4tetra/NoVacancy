import time
import signal
import asyncio

from lib.tunnel.handshake import Handshake

from lib.tunnel.socket.server import TunnelSocketServer, TunnelSocketFactory


class MyClient(TunnelSocketServer):
    def __init__(self, socket_client, address, max_packet_len, block_size, debug):
        super().__init__(socket_client, address, max_packet_len, block_size, debug)
        self.pings = []

    async def packet_callback(self, result):
        if result.category == "ping":
            sent_time = result.get_double()
            current_time = get_time()
            ping = current_time - sent_time
            print("Ping: %0.5f (current: %0.5f, recv: %0.5f)" % (ping, current_time, sent_time))
            self.pings.append(ping)
        elif result.category == "weight":
            print("Weight:", result.get_int(4, signed=True))

start_time = time.monotonic()
def get_time():
    return time.monotonic() - start_time


def ask_exit(tasks):
    for task in tasks:
        task.cancel()


def ask_exit_and_wait(loop, tasks):
    ask_exit(tasks)
    while not all([t.done() for t in tasks]):
        loop.run_until_complete(asyncio.sleep(0.0))


async def read_thread(tunnel_factory):
    while True:
        results = await tunnel_factory.update()
        for result in results:
            if isinstance(result, Handshake):
                print("Received handshake:", result.category, result.packet_num)
        await asyncio.sleep(0.0)


async def write_thread(tunnel_factory):
    last_ping = time.time()
    while True:
        await asyncio.sleep(1.0 / 30.0)
        if time.time() - last_ping > 0.5:
            # tunnel.write_handshake("hand", 0.0, write_interval=0.1)
            tunnel_factory.write("ping", "e", get_time())
            last_ping = time.time()


def main():
    tunnel_factory = TunnelSocketFactory(MyClient, "0.0.0.0", 8080)
    tunnel_factory.start()
    time.sleep(0.25)

    loop = asyncio.get_event_loop()
    tasks = []
    start = time.time()
    tasks.append(asyncio.ensure_future(write_thread(tunnel_factory)))
    tasks.append(asyncio.ensure_future(read_thread(tunnel_factory)))

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, ask_exit, tasks)

    try:
        loop.run_until_complete(asyncio.gather(*tasks))
    # except SessionFinishedException:
    #     ask_exit_and_wait(loop, tasks)
    #     print("SessionFinishedException raised. Exiting")
    except asyncio.CancelledError:
        pass
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)
        tunnel_factory.stop()
        loop.close()
        stop = time.time()
        duration = stop - start

        for tunnel in tunnel_factory.tunnels:
            if len(tunnel.pings) > 0:
                print("mean:", sum(tunnel.pings) / len(tunnel.pings))
                print("len:", len(tunnel.pings))
                print("Num packets sent: ", tunnel.protocol.write_packet_num)
                print("Num packets recv: ", tunnel.protocol.read_packet_num)
                print("Duration: %0.4fs" % duration)
                print("Dropped packets: ", tunnel.protocol.dropped_packet_num)


main()
