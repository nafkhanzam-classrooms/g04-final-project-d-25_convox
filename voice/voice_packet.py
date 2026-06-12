"""Voice packet protocol for UDP streaming."""
import struct
import json
from typing import Optional, Dict, Any

# Voice packet format:
# [4-byte magic][4-byte payload length][payload (JSON)]
VOICE_MAGIC = 0xDEADBEEF


class VoicePacket:
    def __init__(
        self,
        sender: str,
        room: str,
        sequence: int,
        timestamp: int,
        audio_data: bytes,
    ) -> None:
        self.sender = sender
        self.room = room
        self.sequence = sequence
        self.timestamp = timestamp
        self.audio_data = audio_data

    def encode(self) -> bytes:
        """Encode to UDP datagram."""
        import base64

        payload = {
            "type": "VOICE_FRAME",
            "sender": self.sender,
            "room": self.room,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "audio": base64.b64encode(self.audio_data).decode("ascii"),
        }
        json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        length = struct.pack(">I", len(json_bytes))
        magic = struct.pack(">I", VOICE_MAGIC)
        return magic + length + json_bytes

    @staticmethod
    def decode(data: bytes) -> Optional["VoicePacket"]:
        """Decode UDP datagram to VoicePacket."""
        import base64

        if len(data) < 8:
            return None
        magic = struct.unpack(">I", data[0:4])[0]
        if magic != VOICE_MAGIC:
            return None
        length = struct.unpack(">I", data[4:8])[0]
        if len(data) < 8 + length:
            return None
        try:
            payload = json.loads(data[8 : 8 + length].decode("utf-8"))
            audio = base64.b64decode(payload["audio"].encode("ascii"))
            return VoicePacket(
                sender=payload["sender"],
                room=payload["room"],
                sequence=payload["sequence"],
                timestamp=payload["timestamp"],
                audio_data=audio,
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None


class VoiceControl:
    """Control packets for voice management (sent over TCP)."""

    @staticmethod
    def voice_start(room: str, udp_port: int) -> Dict[str, Any]:
        return {
            "type": "VOICE_START",
            "room": room,
            "udp_port": udp_port,
        }

    @staticmethod
    def voice_stop(room: str) -> Dict[str, Any]:
        return {"type": "VOICE_STOP", "room": room}

    @staticmethod
    def voice_status(room: str, user: str, status: str) -> Dict[str, Any]:
        return {
            "type": "VOICE_STATUS",
            "room": room,
            "user": user,
            "status": status,  # "speaking", "muted", "idle"
        }
