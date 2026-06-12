"""Data models for GUI state management."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class UserStatus(Enum):
    """User presence status."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    IN_ROOM = "IN_ROOM"
    IN_MATCH = "IN_MATCH"
    DO_NOT_DISTURB = "DO_NOT_DISTURB"
    VOICE_ACTIVE = "VOICE_ACTIVE"


@dataclass
class User:
    """User model."""
    username: str
    status: UserStatus = UserStatus.OFFLINE
    in_voice: bool = False
    muted: bool = False
    last_seen: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "username": self.username,
            "status": self.status.value,
            "in_voice": self.in_voice,
            "muted": self.muted,
            "last_seen": self.last_seen,
        }


@dataclass
class Message:
    """Chat message model."""
    sender: str
    content: str
    timestamp: str
    room: Optional[str] = None
    target_user: Optional[str] = None
    is_system: bool = False

    def display_text(self) -> str:
        if self.is_system:
            return f"[SYSTEM] {self.content}"
        return f"[{self.timestamp}] {self.sender}: {self.content}"


@dataclass
class Room:
    """Room model."""
    name: str
    owner: str
    members: List[str] = field(default_factory=list)
    max_capacity: int = 50
    visibility: str = "public"
    voice_active: bool = False
    voice_participants: List[str] = field(default_factory=list)
    messages: List[Message] = field(default_factory=list)
    unread_count: int = 0

    def is_member(self, username: str) -> bool:
        return username in self.members

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        if message.sender != "local_user":
            self.unread_count += 1

    def clear_unread(self) -> None:
        self.unread_count = 0


@dataclass
class Friend:
    """Friend model."""
    username: str
    status: UserStatus = UserStatus.OFFLINE
    in_voice: bool = False

    def to_dict(self) -> Dict:
        return {
            "username": self.username,
            "status": self.status.value,
            "in_voice": self.in_voice,
        }


@dataclass
class FileTransfer:
    """File transfer model."""
    transfer_id: str
    filename: str
    filesize: int
    progress: int = 0
    status: str = "pending"  # pending, uploading, complete, error
    error_message: Optional[str] = None

    def is_complete(self) -> bool:
        return self.status == "complete"

    def has_error(self) -> bool:
        return self.status == "error"


class ApplicationModel:
    """Central application data model."""

    def __init__(self):
        self.username: Optional[str] = None
        self.session_token: Optional[str] = None
        self.current_room: str = "global"
        self.current_status: UserStatus = UserStatus.ONLINE

        self.users: Dict[str, User] = {}
        self.rooms: Dict[str, Room] = {}
        self.friends: Dict[str, Friend] = {}
        self.messages: List[Message] = []
        self.file_transfers: Dict[str, FileTransfer] = {}

        # Ensure global room exists
        self.rooms["global"] = Room(name="global", owner="system")

    def set_username(self, username: str) -> None:
        """Set current username."""
        self.username = username

    def set_session_token(self, token: str) -> None:
        """Set session token for reconnect."""
        self.session_token = token

    def add_or_update_user(self, username: str, status: str = "ONLINE", in_voice: bool = False) -> User:
        """Add or update user in model."""
        if username not in self.users:
            self.users[username] = User(username=username)
        user = self.users[username]
        try:
            user.status = UserStatus(status)
        except ValueError:
            user.status = UserStatus.ONLINE
        user.in_voice = in_voice
        return user

    def remove_user(self, username: str) -> None:
        """Remove user from model."""
        self.users.pop(username, None)

    def add_or_update_room(self, room_name: str, owner: str = "system", **kwargs) -> Room:
        """Add or update room in model."""
        if room_name not in self.rooms:
            self.rooms[room_name] = Room(name=room_name, owner=owner)
        room = self.rooms[room_name]
        for key, value in kwargs.items():
            if hasattr(room, key):
                setattr(room, key, value)
        return room

    def remove_room(self, room_name: str) -> None:
        """Remove room from model."""
        self.rooms.pop(room_name, None)

    def add_message(self, sender: str, content: str, timestamp: str, room: Optional[str] = None, is_system: bool = False) -> Message:
        """Add message to model."""
        message = Message(
            sender=sender,
            content=content,
            timestamp=timestamp,
            room=room or self.current_room,
            is_system=is_system,
        )
        self.messages.append(message)

        if room and room in self.rooms:
            self.rooms[room].add_message(message)

        return message

    def get_room_messages(self, room: str) -> List[Message]:
        """Get all messages for a room."""
        if room in self.rooms:
            return self.rooms[room].messages
        return [m for m in self.messages if m.room == room]

    def add_or_update_friend(self, username: str, status: str = "ONLINE", in_voice: bool = False) -> Friend:
        """Add or update friend in model."""
        if username not in self.friends:
            self.friends[username] = Friend(username=username)
        friend = self.friends[username]
        try:
            friend.status = UserStatus(status)
        except ValueError:
            friend.status = UserStatus.ONLINE
        friend.in_voice = in_voice
        return friend

    def remove_friend(self, username: str) -> None:
        """Remove friend from model."""
        self.friends.pop(username, None)

    def add_file_transfer(self, transfer_id: str, filename: str, filesize: int) -> FileTransfer:
        """Add file transfer to model."""
        transfer = FileTransfer(
            transfer_id=transfer_id,
            filename=filename,
            filesize=filesize,
        )
        self.file_transfers[transfer_id] = transfer
        return transfer

    def update_file_transfer_progress(self, transfer_id: str, progress: int) -> Optional[FileTransfer]:
        """Update file transfer progress."""
        if transfer_id in self.file_transfers:
            transfer = self.file_transfers[transfer_id]
            transfer.progress = min(100, progress)
            if progress >= 100:
                transfer.status = "complete"
            else:
                transfer.status = "uploading"
            return transfer
        return None

    def complete_file_transfer(self, transfer_id: str) -> Optional[FileTransfer]:
        """Mark file transfer as complete."""
        if transfer_id in self.file_transfers:
            transfer = self.file_transfers[transfer_id]
            transfer.status = "complete"
            transfer.progress = 100
            return transfer
        return None

    def error_file_transfer(self, transfer_id: str, error_message: str) -> Optional[FileTransfer]:
        """Mark file transfer as errored."""
        if transfer_id in self.file_transfers:
            transfer = self.file_transfers[transfer_id]
            transfer.status = "error"
            transfer.error_message = error_message
            return transfer
        return None
