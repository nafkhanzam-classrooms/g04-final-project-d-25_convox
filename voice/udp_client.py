"""UDP client for sending voice frames."""
import socket
import threading
from queue import Queue
from typing import Optional

from voice.voice_packet import VoicePacket
from utils.logger import get_logger


class UDPVoiceClient:
    def __init__(self, username: str, server_host: str, server_port: int, local_port: int = 0) -> None:
        self.username = username
        self.server_host = server_host
        self.server_port = server_port
        self.local_port = local_port
        self.socket: Optional[socket.socket] = None
        self.current_room: Optional[str] = None
        self.sequence = 0
        self.send_queue: Queue = Queue()
        self.logger = get_logger("UDPVoiceClient")
        self.running = False

    def start(self) -> None:
        """Start UDP voice client."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("127.0.0.1", self.local_port))
        self.local_port = self.socket.getsockname()[1]
        self.running = True
        self.sender_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.sender_thread.start()
        self.receiver_thread.start()
        self.logger.info("UDP voice client started on port %d", self.local_port)

    def _send_loop(self) -> None:
        while self.running:
            try:
                frame_data = self.send_queue.get(timeout=1)
                if frame_data is None:
                    break
                if self.current_room and self.socket:
                    packet = VoicePacket(
                        sender=self.username,
                        room=self.current_room,
                        sequence=self.sequence,
                        timestamp=0,
                        audio_data=frame_data,
                    )
                    self.socket.sendto(packet.encode(), (self.server_host, self.server_port))
                    self.sequence += 1
            except Exception as exc:
                self.logger.exception("Error sending voice frame: %s", exc)

    def _receive_loop(self) -> None:
        while self.running:
            try:
                data, _ = self.socket.recvfrom(4096)
                packet = VoicePacket.decode(data)
                if packet and packet.room == self.current_room:
                    self.on_frame_received(packet)
            except OSError:
                break
            except Exception as exc:
                self.logger.exception("Error receiving voice: %s", exc)

    def send_frame(self, audio_data: bytes) -> None:
        """Queue audio frame for sending."""
        self.send_queue.put(audio_data)

    def on_frame_received(self, packet: VoicePacket) -> None:
        """Override to handle incoming voice frames."""
        pass

    def join_room(self, room: str) -> None:
        """Join voice room."""
        self.current_room = room
        self.sequence = 0
        self.logger.info("%s joined voice room %s", self.username, room)

    def leave_room(self) -> None:
        """Leave voice room."""
        self.logger.info("%s left voice room %s", self.username, self.current_room)
        self.current_room = None

    def stop(self) -> None:
        """Stop UDP voice client."""
        self.running = False
        self.send_queue.put(None)
        if self.socket:
            self.socket.close()
        self.logger.info("UDP voice client stopped")
