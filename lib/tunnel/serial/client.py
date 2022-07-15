import asyncio
import warnings
import serial
import threading

from ..client import TunnelBaseClient

class TunnelSerialClient(TunnelBaseClient):
    """
    Implements TunnelProtocol for serial devices

    Methods
    -------
    start():
        Call this after initialization to start serial connection
    flush():
        Flush serial buffer of all data
    async update():
        Call this in a loop to read all buffered data and run callbacks
    register_callback(category, callback):
        Pass a function reference. When a matching category is received, all registered callbacks will receive the data
    write(category, *args):
        Write data to serial device as a TunnelProtocol packet
    write_handshake(category, *args, write_interval=0.0, timeout=1.0):
        Write data to serial device as a TunnelProtocol packet. Raise an exception in the call to update()
        if a confirming packet isn't received within the specified timeout
    async packet_callback(result):
        Override this method in a subclass. This gets called when any new correctly parsed packet arrives.
    stop():
        Gracefully shutdown the serial device connection
    """

    def __init__(self, address, baud, max_packet_len=128, debug=False):
        """
        :param address: path to arduino device. ex: "/dev/ttyACM0"
        :param baud: communication rate. Must match value defined on the arduino
        """
        super().__init__(max_packet_len, debug)

        # device properties
        self.address = address
        self.baud = baud
        self.device = None

        # a lock to prevent multiple sources from writing to the device at once
        self.write_lock = threading.Lock()

    def start(self):
        """Initializes the serial device"""
        self.device = serial.Serial(self.address, self.baud)

    def flush(self):
        """Flushes all unread characters on the buffer"""
        self.device.flush()

    def _read(self, num_bytes):
        return self.device.read(num_bytes)

    def _write(self, packet):
        """Wrapper for device.write. Locks the device so multiple sources can't write at the same time"""
        with self.write_lock:
            self.device.write(packet)
            if self.debug:
                print("Writing:", packet)

    def stop(self):
        """Gracefully shutdown the serial device connection"""
        self.device.close()
        if len(self.buffer) > 0:
            print("Device message:", self.buffer)
