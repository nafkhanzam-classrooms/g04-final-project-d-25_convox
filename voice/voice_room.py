"""Voice room management system."""
import threading
from typing import Dict, Set, Optional
from dataclasses import dataclass, field

from utils.logger import get_logger


@dataclass
class VoiceParticipant:
    username: str
    speaking: bool = False
    muted: bool = False
    udp_port: Optional[int] = None


class VoiceRoom:
    def __init__(self, room_name: str) -> None:
        self.room_name = room_name
        self.participants: Dict[str, VoiceParticipant] = {}
        self.lock = threading.RLock()
        self.logger = get_logger("VoiceRoom")

    def add_participant(self, username: str, udp_port: int) -> None:
        with self.lock:
            participant = VoiceParticipant(username=username, udp_port=udp_port)
            self.participants[username] = participant
            self.logger.info("%s joined voice room %s", username, self.room_name)

    def remove_participant(self, username: str) -> None:
        with self.lock:
            self.participants.pop(username, None)
            self.logger.info("%s left voice room %s", username, self.room_name)

    def set_speaking(self, username: str, speaking: bool) -> None:
        with self.lock:
            if username in self.participants:
                self.participants[username].speaking = speaking

    def set_muted(self, username: str, muted: bool) -> None:
        with self.lock:
            if username in self.participants:
                self.participants[username].muted = muted

    def get_participants(self) -> list[str]:
        with self.lock:
            return list(self.participants.keys())

    def get_participant(self, username: str) -> Optional[VoiceParticipant]:
        with self.lock:
            return self.participants.get(username)

    def is_member(self, username: str) -> bool:
        with self.lock:
            return username in self.participants

    def get_speaking_users(self) -> list[str]:
        with self.lock:
            return [u for u, p in self.participants.items() if p.speaking and not p.muted]

    def participant_count(self) -> int:
        with self.lock:
            return len(self.participants)


class VoiceRoomManager:
    def __init__(self) -> None:
        self.rooms: Dict[str, VoiceRoom] = {}
        self.lock = threading.RLock()
        self.logger = get_logger("VoiceRoomManager")

    def create_or_get_room(self, room_name: str) -> VoiceRoom:
        with self.lock:
            if room_name not in self.rooms:
                self.rooms[room_name] = VoiceRoom(room_name)
            return self.rooms[room_name]

    def get_room(self, room_name: str) -> Optional[VoiceRoom]:
        with self.lock:
            return self.rooms.get(room_name)

    def add_to_room(self, room_name: str, username: str, udp_port: int) -> None:
        room = self.create_or_get_room(room_name)
        room.add_participant(username, udp_port)

    def remove_from_room(self, room_name: str, username: str) -> None:
        with self.lock:
            room = self.rooms.get(room_name)
            if room:
                room.remove_participant(username)
                if room.participant_count() == 0:
                    self.rooms.pop(room_name, None)
                    self.logger.info("Deleted empty voice room %s", room_name)

    def list_rooms(self) -> list[str]:
        with self.lock:
            return list(self.rooms.keys())

    def user_voice_room(self, username: str) -> Optional[str]:
        with self.lock:
            for room_name, room in self.rooms.items():
                if room.is_member(username):
                    return room_name
        return None
