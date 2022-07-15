import time
import asyncio
import logging
from lib.tunnel.socket.server import TunnelSocketServer
from lib.tunnel.result import PacketResult


class NoVacancyTunnelClient(TunnelSocketServer):
    """Wrapper class for TunnelSocketServer adds functionality specific to the NoVacancy system"""

    def __init__(self, logger: logging.Logger):
        """
        :param logger: logger object generated from LoggerManager
        """
        super().__init__("0.0.0.0", 8080)
        self.logger = logger
        self.protocol.use_double_precision = True
        self.start_time = time.monotonic()  # timer for ping

    async def packet_callback(self, result: PacketResult):
        """
        Callback for when a new packet is received
        :param result: PacketResult object containing data within the packet
        :return: None
        """
        board_id = result.get_int(4, signed=False)
        if result.category == "ping":
            sent_time = result.get_float()
            current_time = self.get_time()
            ping = current_time - sent_time
            self.logger.info("Ping: %0.5f (current: %0.5f, recv: %0.5f)" % (ping, current_time, sent_time))
            await asyncio.sleep(0.0)

    def get_time(self):
        """Get the time since __init__ was called"""
        return time.monotonic() - self.start_time

    def write_ping(self):
        """Write a ping message. Called externally"""
        self.write("ping", self.get_time())
