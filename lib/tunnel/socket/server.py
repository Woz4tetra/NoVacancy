import socket
import time
import warnings
import threading
from queue import Queue

from lib.tunnel.util import *

from ..client import TunnelBaseClient


class TunnelSocketFactory:
    def __init__(self, tunnel_client_class, address, port, max_packet_len=128, block_size=1024, debug=False, **kwargs):
        self.address = address
        self.port = port
        self.block_size = block_size
        self.max_packet_len = max_packet_len
        self.debug = debug
        self.tunnel_client_class = tunnel_client_class
        self.client_class_kwargs = kwargs

        self._socket_thread = threading.Thread(target=self._socket_task)
        self._task_flag = True
        self._clients_queue = Queue()

        self.tunnels = []

    def _socket_task(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(2.0)

        sock.bind((self.address, self.port))
        sock.listen(0)

        while self._task_flag:
            try:
                client, address = sock.accept()
            except socket.timeout:
                time.sleep(0.1)
                continue
            client.settimeout(1.0)
            self._clients_queue.put((client, address))
    
    def iter_tunnels(self):
        for tunnel in self.tunnels:
            yield tunnel

    def start(self):
        self._socket_thread.start()
    
    def _check_clients(self):
        delete_indices = []
        for index, tunnel in enumerate(self.tunnels):
            if not tunnel.is_running:
                delete_indices.append(index)
            for index in delete_indices[::-1]:
                self.tunnels.pop(index)
        
        while not self._clients_queue.empty():
            client, address = self._clients_queue.get()
            tunnel = self.tunnel_client_class(client, address, self.max_packet_len, self.block_size, self.debug, **self.client_class_kwargs)
            tunnel.start()
            self.tunnels.append(tunnel)
    
    async def update(self):
        self._check_clients()
        all_results = []
        for tunnel in self.tunnels:
            results = await tunnel.update()
            all_results.extend(results)
        return all_results
    
    def write(self, category, formats, *args):
        for tunnel in self.tunnels:
            tunnel.write(category, formats, *args)
    
    def stop(self):
        self._task_flag = False
        for tunnel in self.tunnels:
            tunnel.stop()


class TunnelSocketServer(TunnelBaseClient):
    def __init__(self, socket_client, address, max_packet_len=128, block_size=1024, debug=False, **kwargs):
        super().__init__(max_packet_len, debug)

        # device properties
        self.address = address
        self.socket_client = socket_client
        self.block_size = block_size

        self.is_running = False

        self.client_lock = threading.Lock()

    def start(self):
        """Initializes the socket device"""
        self.is_running = True

    def flush(self):
        """Flushes all unread characters on the buffer"""

    def available(self):
        return self.block_size

    def _read(self, num_bytes):
        if not self.is_running:
            return b""
        with self.client_lock:
            try:
                content = self.socket_client.recv(num_bytes)
            except socket.timeout:
                print("%s timeout" % str(self.address))
                return b""
            except BaseException as e:
                warnings.warn(e)
                self.stop()
                return b""

            if len(content) == 0:
                self.stop()
                return b""
            return content

    def _write(self, packet):
        if not self.is_running:
            return
        with self.client_lock:
            try:
                self.socket_client.sendall(packet)
            except BaseException as e:
                warnings.warn(e)
                self.stop()

    def stop(self):
        self.is_running = False
