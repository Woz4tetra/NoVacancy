import socket
import time
import warnings
import threading
from queue import Queue

from lib.tunnel.util import *

from ..client import TunnelBaseClient


class ClientContainer:
    def __init__(self, client):
        self.client = client
        self._queue = Queue()
        self._run_flag = True
        self._lock = threading.Lock()
        self._read_buffer = b""

    def queue(self, packet: bytes):
        with self._lock:
            self._queue.put(packet)
    
    def deque(self):
        with self._lock:
            return self._queue.get()
    
    def is_empty(self):
        with self._lock:
            return self._queue.empty()
    
    def should_run(self):
        with self._lock:
            return self._run_flag
    
    def set_run(self, state: bool):
        with self._lock:
            self._run_flag = state
            if not state:
                self.client.close()

    def send(self, packet: bytes):
        with self._lock:
            self.client.send(packet)
    
    def recv(self, block_size: int):
        with self._lock:
            return self.client.recv(block_size)
    
    def get_buffer(self):
        return self._read_buffer
    
    def set_buffer(self, buffer: bytes):
        with self._lock:
            self._read_buffer = buffer


class TunnelSocketServer(TunnelBaseClient):
    def __init__(self, address, port, max_packet_len=128, block_size=1024, connect_timeout=1.0, read_timeout=1.0, update_delay=0.001, debug=False):
        super().__init__(max_packet_len, debug)

        # device properties
        self.address = address
        self.port = port
        self.device = None

        self.block_size = block_size
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.update_delay = update_delay

        self.socket_thread = threading.Thread(target=self._socket_server_task)
        self.socket_run_flag = True

        self.clients = []

        self.socket_buffer = b""
        self.read_lock = threading.Lock()
        self.clients_lock = threading.Lock()

    def _socket_server_task(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(self.connect_timeout)
        while self.socket_run_flag:
            try:
                sock.bind((self.address, self.port))
                sock.listen(0)
                break
            except OSError as e:
                warnings.warn(str(e))
                time.sleep(0.1)

        while self.socket_run_flag:
            # with self.clients_lock:
            #     delete_indices = []
            #     for index, container in enumerate(self.clients):
            #         if not container.should_run():
            #             delete_indices.append(index)
            #     for index in delete_indices[::-1]:
            #         self.clients.pop(index)

            try:
                if self.debug:
                    print("Waiting for new connection")
                client, addr = sock.accept()
            except socket.timeout:
                time.sleep(0.1)
                continue

            if self.debug:
                print("Opening new connection:", addr)
            client.settimeout(self.read_timeout)
            container = ClientContainer(client)
            self.clients.append(container)
            # client_thread = threading.Thread(target=self._socket_client_task, args=(container,))
            # client_thread.start()
            while self.socket_run_flag:
                try:
                    content = client.recv(self.block_size)
                except socket.timeout:
                    print("read timeout")
                    continue
                if len(content) == 0:
                    break
                print(content)

        for container in self.clients:
            container.set_run(False)

    # def _socket_client_task(self, container: ClientContainer):
        # while True:
        #     if not container.should_run():
        #         break
        #     try:
        #         content = container.recv(self.block_size)
        #         if len(content) == 0:
        #             break
        #         container.set_buffer(container.get_buffer() + content)
        #     except socket.timeout:
        #         pass
        #     if container.is_empty():
        #         time.sleep(self.update_delay)
        #         continue
        #     packet = container.deque()
        #     if self.debug:
        #         print("Dequeued: " + str(packet))
        #     container.send(packet)
        # container.set_run(False)

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
        for container in self.clients:
            container.queue(packet)
        if self.debug:
            print("Writing:", packet)

    def stop(self):
        """Gracefully shutdown the device connection"""
        self.socket_run_flag = False
        if len(self.buffer) > 0:
            print("Device message:", self.buffer)
