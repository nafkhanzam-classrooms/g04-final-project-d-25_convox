"""UDP voice server for realtime relay."""
import socket
import threading
from typing import Dict, Optional

from voice.voice_packet import VoicePacket
from voice.voice_room import VoiceRoomManager
from utils.logger import get_logger


class VoiceClient:
    def __init__(self, username: str, address: tuple) -> None:
        self.username = username
        self.address = address  # (host, port)


class UDPVoiceServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 9001) -> None:
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.room_manager = VoiceRoomManager()
        self.clients: Dict[str, VoiceClient] = {}
        self.lock = threading.RLock()
        self.logger = get_logger("UDPVoiceServer")
        self.running = False

    def start(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.logger.info("UDP voice server listening on %s:%s", self.host, self.port)
        self.running = True
        self.receiver_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.receiver_thread.start()

    def receive_loop(self) -> None:
        while self.running:
            try:
                data, address = self.socket.recvfrom(4096)
                packet = VoicePacket.decode(data)
                if packet:
                    self.relay_packet(packet, address)
            except OSError:
                break
            except Exception as exc:
                self.logger.exception("Error in receive loop: %s", exc)

    def relay_packet(self, packet: VoicePacket, sender_address: tuple) -> None:
        room = self.room_manager.get_room(packet.room)
        if not room:
            return

        participants = room.get_participants()
        for participant_name in participants:
            if participant_name == packet.sender:
                continue

            participant = room.get_participant(participant_name)
            if participant and participant.udp_port:
                try:
                    self.socket.sendto(packet.encode(), (sender_address[0], participant.udp_port))
                except OSError as exc:
                    self.logger.warning("Failed to send to %s: %s", participant_name, exc)

    def register_client(self, username: str, room: str, udp_port: int) -> None:
        with self.lock:
            self.clients[username] = VoiceClient(username, ("127.0.0.1", udp_port))
        self.room_manager.add_to_room(room, username, udp_port)
        self.logger.info("Registered %s in voice room %s (port %s)", username, room, udp_port)

    def unregister_client(self, username: str) -> None:
        room = self.room_manager.user_voice_room(username)
        if room:
            self.room_manager.remove_from_room(room, username)
        with self.lock:
            self.clients.pop(username, None)
        self.logger.info("Unregistered %s from voice", username)

    def stop(self) -> None:
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.info("UDP voice server stopped")
