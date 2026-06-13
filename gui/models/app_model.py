"""Central application model holding the GUI's mirror of server state.

The model is plain Python (no Qt) so it can be inspected and tested in
isolation. Widgets read from it and never mutate server state directly;
mutations come from the TCP controller via the event dispatcher.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from gui.models.message_model import Message, MessageKind
from gui.models.room_model import Room
from gui.models.user_model import Friend, User, UserStatus


@dataclass
class FileTransfer:
    """Tracking state for an active file upload/download."""

    transfer_id: str
    filename: str
    filesize: int
    progress: int = 0
    status: str = "pending"  # pending | uploading | complete | error
    error_message: Optional[str] = None

    def is_complete(self) -> bool:
        return self.status == "complete"

    def has_error(self) -> bool:
        return self.status == "error"


class ApplicationModel:
    """Central state container for the GUI client."""

    def __init__(self) -> None:
        self.username: Optional[str] = None
        self.session_token: Optional[str] = None
        self.current_room: str = "global"
        self.current_status: UserStatus = UserStatus.ONLINE

        self.users: Dict[str, User] = {}
        self.rooms: Dict[str, Room] = {"global": Room(name="global", owner="system")}
        self.friends: Dict[str, Friend] = {}
        self.messages: List[Message] = []
        self.file_transfers: Dict[str, FileTransfer] = {}

    # ------------------------------------------------------------------ session
    def set_username(self, username: str) -> None:
        self.username = username

    def set_session_token(self, token: str) -> None:
        self.session_token = token

    # -------------------------------------------------------------------- users
    def add_or_update_user(
        self,
        username: str,
        status: str = "ONLINE",
        in_voice: bool = False,
    ) -> User:
        user = self.users.get(username) or User(username=username)
        user.status = UserStatus.coerce(status)
        user.in_voice = in_voice
        self.users[username] = user
        return user

    def remove_user(self, username: str) -> None:
        self.users.pop(username, None)

    # -------------------------------------------------------------------- rooms
    def add_or_update_room(self, room_name: str, owner: str = "system", **kwargs: object) -> Room:
        room = self.rooms.get(room_name) or Room(name=room_name, owner=owner)
        for key, value in kwargs.items():
            if hasattr(room, key):
                setattr(room, key, value)
        self.rooms[room_name] = room
        return room

    def remove_room(self, room_name: str) -> None:
        if room_name == "global":
            return
        self.rooms.pop(room_name, None)

    # ----------------------------------------------------------------- messages
    def add_message(
        self,
        sender: str,
        content: str,
        timestamp: str = "",
        room: Optional[str] = None,
        target_user: Optional[str] = None,
        is_system: bool = False,
        kind: Optional[MessageKind] = None,
    ) -> Message:
        if kind is None:
            if is_system:
                kind = MessageKind.SYSTEM
            elif target_user is not None:
                kind = MessageKind.PRIVATE
            elif sender == self.username:
                kind = MessageKind.SELF
            else:
                kind = MessageKind.NORMAL

        message = Message(
            sender=sender,
            content=content,
            timestamp=timestamp,
            room=room or self.current_room,
            target_user=target_user,
            kind=kind,
        )
        self.messages.append(message)

        target_room = room or (self.current_room if not target_user else None)
        if target_room:
            self.add_or_update_room(target_room).add_message(message)
        return message

    def get_room_messages(self, room: str) -> List[Message]:
        if room in self.rooms:
            return self.rooms[room].messages
        return [m for m in self.messages if m.room == room]

    # ------------------------------------------------------------------ friends
    def add_or_update_friend(
        self,
        username: str,
        status: str = "OFFLINE",
        in_voice: bool = False,
        pending: bool = False,
    ) -> Friend:
        friend = self.friends.get(username) or Friend(username=username)
        friend.status = UserStatus.coerce(status)
        friend.in_voice = in_voice
        friend.pending = pending
        self.friends[username] = friend
        return friend

    def remove_friend(self, username: str) -> None:
        self.friends.pop(username, None)

    # ---------------------------------------------------------------- transfers
    def add_file_transfer(self, transfer_id: str, filename: str, filesize: int) -> FileTransfer:
        transfer = FileTransfer(transfer_id=transfer_id, filename=filename, filesize=filesize)
        self.file_transfers[transfer_id] = transfer
        return transfer

    def update_file_transfer_progress(
        self, transfer_id: str, progress: int
    ) -> Optional[FileTransfer]:
        transfer = self.file_transfers.get(transfer_id)
        if not transfer:
            return None
        transfer.progress = max(0, min(100, progress))
        transfer.status = "complete" if transfer.progress >= 100 else "uploading"
        return transfer

    def complete_file_transfer(self, transfer_id: str) -> Optional[FileTransfer]:
        transfer = self.file_transfers.get(transfer_id)
        if transfer:
            transfer.progress = 100
            transfer.status = "complete"
        return transfer

    def error_file_transfer(self, transfer_id: str, error_message: str) -> Optional[FileTransfer]:
        transfer = self.file_transfers.get(transfer_id)
        if transfer:
            transfer.status = "error"
            transfer.error_message = error_message
        return transfer


__all__ = [
    "ApplicationModel",
    "FileTransfer",
    "Friend",
    "Message",
    "MessageKind",
    "Room",
    "User",
    "UserStatus",
]
