import socket
import time
import warnings
import threading
from queue import Queue

from lib.tunnel.util import *

from ..client import TunnelBaseClient


class TunnelSocketClient(TunnelBaseClient):
    def __init__(self, address, port, max_packet_len=128, block_size=1024, timeout=5, debug=False):
        super().__init__(max_packet_len, debug)

        # device properties
        self.address = address
        self.port = port
        self.device = None

        self.block_size = block_size
        self.timeout = timeout

        self.socket_thread = threading.Thread(target=self._socket_client_task)
        self.socket_run_flag = True

        self.sock = None

        self.socket_buffer = b""
        self.read_lock = threading.Lock()
        self.write_lock = threading.Lock()

    def _socket_client_task(self):
        while self.socket_run_flag:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            try:
                self.sock.connect((self.address, self.port))
            except BaseException as e:
                warnings.warn(str(e))
                time.sleep(0.1)
                continue
            if self.debug:
                print("Opening new connection:", self.address)
            
            while True:
                if not self.socket_run_flag:
                    break
                content = self.sock.recv(self.block_size)
                if len(content) == 0:
                    break
                with self.read_lock:
                    self.socket_buffer += content
        self.sock.close()

    def start(self):
        """Initializes the socket device"""
        self.socket_thread.start()

    def flush(self):
        """Flushes all unread characters on the buffer"""
        with self.read_lock:
            self.socket_buffer = b""

    def available(self):
        return self.block_size

    def _read(self, num_bytes):
        """Reads requested number of bytes (or less) from device"""
        read_len = min(num_bytes, len(self.socket_buffer))
        with self.read_lock:
            read_bytes = self.socket_buffer[0:read_len]
            self.socket_buffer = self.socket_buffer[read_len:]
            return read_bytes

    def _write(self, packet):
        """Wrapper for device.write. Locks the device so multiple sources can't write at the same time"""
        with self.write_lock:
            try:
                self.sock.sendall(packet)
            except BaseException as e:
                warnings.warn(str(e))
                return
            if self.debug:
                print("Writing:", packet)

    def stop(self):
        """Gracefully shutdown the device connection"""
        self.socket_run_flag = False
        if len(self.buffer) > 0:
            print("Device message:", self.buffer)
