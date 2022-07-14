import time
import signal
import asyncio

from lib.tunnel.handshake import Handshake

from lib.tunnel.socket.client import TunnelSocketClient


class MyClient(TunnelSocketClient):
    def __init__(self, address, port):
        super().__init__(address, port, debug=False)

    async def packet_callback(self, result):
        if result.category == "ping":
            print("Received ping")
            self.write("ping", "e", result.get_double())


def ask_exit(tasks):
    for task in tasks:
        task.cancel()


def ask_exit_and_wait(loop, tasks):
    ask_exit(tasks)
    while not all([t.done() for t in tasks]):
        loop.run_until_complete(asyncio.sleep(0.0))


async def read_thread(tunnel):
    while True:
        results = await tunnel.update()
        for result in results:
            if isinstance(result, Handshake):
                print("Received handshake:", result.category, result.packet_num)
        await asyncio.sleep(0.0)


def main():
    tunnel = MyClient("127.0.0.1", 8080)
    tunnel.start()
    time.sleep(0.25)

    loop = asyncio.get_event_loop()
    tasks = []
    tasks.append(asyncio.ensure_future(read_thread(tunnel)))

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
        tunnel.stop()
        loop.close()

main()
