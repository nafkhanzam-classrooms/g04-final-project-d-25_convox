import socket
import threading
from typing import Dict, Iterable, Optional

from protocol.packet import PacketType, build_packet


class ConnectionManager:
    def __init__(self):
        self.clients: Dict[str, socket.socket] = {}
        self.lock = threading.RLock()

    def add(self, username: str, conn: socket.socket) -> None:
        with self.lock:
            self.clients[username] = conn

    def remove(self, username: str) -> None:
        with self.lock:
            self.clients.pop(username, None)

    def get(self, username: str) -> Optional[socket.socket]:
        with self.lock:
            return self.clients.get(username)

    def list_usernames(self) -> list[str]:
        with self.lock:
            return sorted(self.clients.keys())

    def send(self, username: str, packet_type: PacketType, **fields: object) -> bool:
        conn = self.get(username)
        if conn is None:
            return False
        packet = build_packet(packet_type, **fields)
        try:
            conn.sendall(packet)
            return True
        except OSError:
            return False

    def broadcast(self, recipients: Iterable[str], packet_type: PacketType, **fields: object) -> None:
        for username in recipients:
            self.send(username, packet_type, **fields)
