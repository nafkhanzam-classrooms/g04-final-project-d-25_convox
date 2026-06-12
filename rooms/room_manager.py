from dataclasses import dataclass, field
import threading
from typing import Dict, Optional, Set

from database.db import Database


@dataclass
class Room:
    name: str
    owner: str
    visibility: str = "public"
    max_capacity: int = 50
    invite_only: bool = False
    password: Optional[str] = None
    members: Set[str] = field(default_factory=set)
    invites: Set[str] = field(default_factory=set)


class RoomManager:
    def __init__(self, database: Database):
        self.database = database
        self.rooms: Dict[str, Room] = {}
        self.lock = threading.RLock()
        if self.database.get_room("global") is None:
            self.database.create_room("global", "system", visibility="public", max_capacity=999, invite_only=False, password=None)
        self._load_room("global")

    def _load_room(self, room_name: str) -> Optional[Room]:
        with self.lock:
            if room_name in self.rooms:
                return self.rooms[room_name]
            room_record = self.database.get_room(room_name)
            if not room_record:
                return None
            room = Room(
                name=room_record["name"],
                owner=self.database.find_username(room_record["owner_id"]) or "system",
                visibility=room_record["visibility"],
                max_capacity=room_record["max_capacity"],
                invite_only=bool(room_record["invite_only"]),
                password=room_record["password"],
            )
            room.members = set(self.database.list_room_members(room_name))
            self.rooms[room_name] = room
            return room

    def create_room(
        self,
        room_name: str,
        owner: str,
        visibility: str = "public",
        max_capacity: int = 50,
        invite_only: bool = False,
        password: Optional[str] = None,
    ) -> bool:
        with self.lock:
            if self.database.get_room(room_name) is not None:
                return False
            created = self.database.create_room(room_name, owner, visibility, max_capacity, invite_only, password)
            if not created:
                return False
            room = Room(
                name=room_name,
                owner=owner,
                visibility=visibility,
                max_capacity=max_capacity,
                invite_only=invite_only,
                password=password,
            )
            room.members.add(owner)
            self.database.add_room_member(room_name, owner)
            self.rooms[room_name] = room
            return True

    def join_room(self, room_name: str, username: str, password: Optional[str] = None) -> tuple[Optional[Room], Optional[str]]:
        with self.lock:
            room = self.get_room(room_name)
            if room is None:
                return None, f"Room '{room_name}' does not exist."
            if room.invite_only and username not in room.invites and username != room.owner and not self.database.is_room_invited(room_name, username):
                return None, f"Room '{room_name}' is invite-only."
            if room.password and room.password != password:
                return None, "Incorrect room password."
            if len(room.members) >= room.max_capacity:
                return None, f"Room '{room_name}' is full."
            room.members.add(username)
            self.database.add_room_member(room_name, username)
            return room, None

    def leave_room(self, room_name: str, username: str) -> None:
        with self.lock:
            room = self.get_room(room_name)
            if room is None:
                return
            room.members.discard(username)
            self.database.remove_room_member(room_name, username)
            if room_name.startswith("match_") and not room.members:
                self.delete_room(room_name)

    def invite_user(self, room_name: str, username: str) -> None:
        with self.lock:
            room = self.get_room(room_name)
            if room is None:
                raise ValueError(f"Room '{room_name}' does not exist.")
            room.invites.add(username)

    def kick_user(self, room_name: str, username: str) -> None:
        with self.lock:
            room = self.get_room(room_name)
            if room is None:
                raise ValueError(f"Room '{room_name}' does not exist.")
            room.members.discard(username)
            self.database.remove_room_member(room_name, username)

    def delete_room(self, room_name: str) -> None:
        with self.lock:
            if room_name in self.rooms:
                del self.rooms[room_name]
            self.database.delete_room(room_name)

    def get_room(self, room_name: str) -> Optional[Room]:
        with self.lock:
            return self.rooms.get(room_name) or self._load_room(room_name)

    def is_owner(self, room_name: str, username: str) -> bool:
        room = self.get_room(room_name)
        return room is not None and room.owner == username

    def is_room_member(self, room_name: str, username: str) -> bool:
        room = self.get_room(room_name)
        return room is not None and username in room.members

    def get_members(self, room_name: str) -> Set[str]:
        room = self.get_room(room_name)
        return set(room.members) if room else set()

    def list_rooms(self) -> list[str]:
        with self.lock:
            return sorted(self.rooms.keys())

    def get_room_owner(self, room_name: str) -> Optional[str]:
        room = self.get_room(room_name)
        return room.owner if room else None
