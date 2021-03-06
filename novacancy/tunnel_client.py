import time
import asyncio
from lib.tunnel.socket.server import TunnelSocketServer
from lib.tunnel.result import PacketResult


class DeviceType:
    NULL = -1
    BOOTH = 0
    DOOR = 1
    BIGSIGN = 2

    @classmethod
    def get_occupancy_types(cls):
        return cls.BOOTH, cls.DOOR


class NoVacancyTunnelClient(TunnelSocketServer):
    """Wrapper class for TunnelSocketServer adds functionality specific to the NoVacancy system"""

    def __init__(self, socket_client, address, max_packet_len, block_size, debug, **kwargs):
        super().__init__(socket_client, address, max_packet_len, block_size, debug)
        self.logger = kwargs.get("logger")
        self.config = kwargs.get("config")
        self.start_time = time.monotonic()  # timer for ping
        self.board_id = ""
        self.board_type = -1
        self.prev_heartbeat_remote = 0
        self.prev_heartbeat_local = 0.0
        self.heartbeat_interval = 1.0

        self.weight = 0
        self.distance = 0.0
        self.latch = False

    async def packet_callback(self, result: PacketResult):
        """
        Callback for when a new packet is received
        :param result: PacketResult object containing data within the packet
        :return: None
        """
        if result.category == "ping":
            sent_time = result.get_double()
            current_time = self.get_time()
            ping = current_time - sent_time
            self.logger.info("Ping %s: %0.5f (current: %0.5f, recv: %0.5f)" % (self.board_id, ping, current_time, sent_time))
            await asyncio.sleep(0.0)
        elif result.category == "heart":
            board_id = str(result.get_int(4, signed=False))
            self.board_type = result.get_int(4, signed=False)
            self.prev_heartbeat_remote = result.get_int(4, signed=False)
            self.prev_heartbeat_local = time.monotonic()
            if self.board_id != board_id:
                if self.board_id != -1:
                    self.logger.warn("Board ID for client changed from %s to %s" % (self.board_id, board_id))
                self.board_id = board_id
                self.logger.info("Board ID for %s is %s" % (self.address, self.board_id))
            self.board_id = board_id
        elif result.category == "weight":
            self.weight = result.get_int(4, signed=True)
        elif result.category == "dist":
            self.distance = result.get_float()
        elif result.category == "latch":
            self.latch = result.get_bool()

    def get_occupancy(self):
        """Return True if occupied, False if vacant"""
        if self.board_type == DeviceType.NULL:
            self.logger.warn("Board %s's type has not been set" % self.board_id)
            return False
        elif self.board_type == DeviceType.BOOTH:
            weight_threshold = self.get_weight_threshold()
            weight_direction = self.get_weight_threshold_direction()
            distance_threshold = self.get_distance_threshold()
            self.logger.debug("Board ID: %s. Weight = %s, Distance = %s" % (self.board_id, self.weight, self.distance))
            occupancy = False
            if weight_direction:
                occupancy |= self.weight > weight_threshold
            else:
                occupancy |= self.weight < weight_threshold
            occupancy |= 0.1 < self.distance < distance_threshold
            return occupancy
        elif self.board_type == DeviceType.DOOR:
            self.logger.debug("Board ID: %s. Latch = %s" % (self.board_id, self.latch))
            return self.latch

    def get_weight_threshold(self):
        return self.config.devices.get_nested_default(("weights", self.board_id), -70000)

    def get_weight_threshold_direction(self):
        return self.config.devices.get_nested_default(("weight_directions", self.board_id), False)

    def get_distance_threshold(self):
        return self.config.devices.get_nested_default(("distances", self.board_id), 170.0)

    def get_heartbeat(self):
        return time.monotonic() - self.prev_heartbeat_local

    def is_stale(self):
        return self.get_heartbeat() > self.heartbeat_interval * 2.0

    def set_bigsign(self, occupancy: bool):
        """True if occupied, False if vacant"""
        self.write_handshake("bigsign", "c", occupancy)

    def set_led(self, pattern: str):
        self.write_handshake("led", "s", pattern)

    def set_volume(self, volume: int):
        # lower numbers == louder volume!
        self.write_handshake("volume", "c", volume)

    def get_board_id(self):
        return self.board_id

    def get_board_type(self):
        return self.board_type
    
    def is_occupancy_device(self):
        return self.board_type in DeviceType.get_occupancy_types()

    def get_time(self):
        """Get the time since __init__ was called"""
        return time.monotonic() - self.start_time

    def write_ping(self):
        """Write a ping message. Called externally"""
        self.write("ping", "e", self.get_time())

    def stop(self):
        super().stop()
        self.logger.info("Client %s is stopping" % str(self.address))
