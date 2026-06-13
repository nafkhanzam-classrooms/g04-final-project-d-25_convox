"""GUI state manager - single source of truth for the desktop client.

Lives entirely on the GUI thread. Listens to the event dispatcher (which
is fed by the TCP worker thread via Qt signals - so handlers here run on
the GUI thread, no locking needed) and updates the central
``ApplicationModel`` accordingly. Re-emits convenience signals widgets
can subscribe to without having to know about packet structures.
"""

from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from gui.controllers.event_dispatcher import EventDispatcher, get_dispatcher
from gui.models.app_model import ApplicationModel
from gui.models.message_model import MessageKind
from gui.models.user_model import UserStatus
from utils.logger import get_logger


class GuiStateManager(QObject):
    """Bridges the event dispatcher and the application model."""

    # Emitted whenever a message lands so widgets can refresh selectively.
    message_added = pyqtSignal(str)         # room (or "@private")
    rooms_changed = pyqtSignal()
    users_changed = pyqtSignal()
    friends_changed = pyqtSignal()
    status_changed = pyqtSignal(str)        # current status string

    def __init__(
        self,
        model: Optional[ApplicationModel] = None,
        dispatcher: Optional[EventDispatcher] = None,
    ) -> None:
        super().__init__()
        self.model = model or ApplicationModel()
        self.dispatcher = dispatcher or get_dispatcher()
        self.logger = get_logger("GuiStateManager")
        self._wire_signals()

    # ------------------------------------------------------------------ wiring
    def _wire_signals(self) -> None:
        d = self.dispatcher
        d.session_restored.connect(self._on_session)
        d.message_received.connect(self._on_message)
        d.private_message_received.connect(self._on_private_message)
        d.system_message.connect(self._on_system_message)
        d.online_users_updated.connect(self._on_online_users)
        d.user_status_changed.connect(self._on_user_status)
        d.friend_list_updated.connect(self._on_friend_list)
        d.friend_request_received.connect(self._on_friend_request)
        d.room_joined.connect(self._on_room_joined)
        d.room_left.connect(self._on_room_left)
        d.room_deleted.connect(self._on_room_deleted)
        d.room_list_updated.connect(self._on_room_list)
        d.file_transfer_started.connect(self._on_transfer_start)
        d.file_transfer_progress.connect(self._on_transfer_progress)
        d.file_transfer_complete.connect(self._on_transfer_complete)
        d.file_transfer_error.connect(self._on_transfer_error)
        d.image_received.connect(self._on_image_or_file)

    # ----------------------------------------------------------------- helpers
    def set_identity(self, username: str, session_token: Optional[str] = None) -> None:
        """Bind the local identity once login succeeds."""
        self.model.set_username(username)
        if session_token:
            self.model.set_session_token(session_token)

    def set_status(self, status: str) -> None:
        self.model.current_status = UserStatus.coerce(status)
        self.status_changed.emit(self.model.current_status.value)

    def set_current_room(self, room: str) -> None:
        self.model.current_room = room
        room_obj = self.model.add_or_update_room(room)
        room_obj.clear_unread()
        self.rooms_changed.emit()

    def record_outgoing_message(self, room: str, content: str, timestamp: str = "") -> None:
        """Echo locally sent messages into the model."""
        self.model.add_message(
            sender=self.model.username or "me",
            content=content,
            timestamp=timestamp,
            room=room,
            kind=MessageKind.SELF,
        )
        self.message_added.emit(room)

    def record_outgoing_private(self, target: str, content: str, timestamp: str = "") -> None:
        self.model.add_message(
            sender=self.model.username or "me",
            content=content,
            timestamp=timestamp,
            target_user=target,
            kind=MessageKind.SELF,
        )
        self.message_added.emit(f"@{target}")

    # ----------------------------------------------------------------- handlers
    def _on_session(self, username: str, room: str) -> None:
        self.model.set_username(username)
        self.set_current_room(room or "global")

    def _on_message(self, room: str, sender: str, message: str, timestamp: str) -> None:
        own = sender == self.model.username
        kind = MessageKind.SELF if own else MessageKind.NORMAL
        self.model.add_message(sender, message, timestamp, room=room, kind=kind)
        if not own and room != self.model.current_room:
            self.model.add_or_update_room(room).increment_unread()
            self.rooms_changed.emit()
        self.message_added.emit(room)

    def _on_private_message(self, sender: str, message: str, timestamp: str) -> None:
        self.model.add_message(
            sender=sender,
            content=message,
            timestamp=timestamp,
            target_user=self.model.username,
            kind=MessageKind.PRIVATE,
        )
        self.message_added.emit(f"@{sender}")

    def _on_system_message(self, room: str, message: str) -> None:
        self.model.add_message("system", message, room=room, is_system=True)
        self.message_added.emit(room)

    def _on_online_users(self, users: List[str]) -> None:
        for user in users:
            self.model.add_or_update_user(user, status="ONLINE")
        # Mark anyone not in the list as offline
        seen = set(users)
        for username, user in list(self.model.users.items()):
            if username not in seen and username != self.model.username:
                user.status = UserStatus.OFFLINE
        self.users_changed.emit()

    def _on_user_status(self, user: str, status: str) -> None:
        self.model.add_or_update_user(user, status=status)
        if user in self.model.friends:
            self.model.add_or_update_friend(
                user,
                status=status,
                in_voice=self.model.friends[user].in_voice,
                pending=self.model.friends[user].pending,
            )
            self.friends_changed.emit()
        self.users_changed.emit()

    def _on_friend_list(self, friends: List[dict]) -> None:
        self.model.friends.clear()
        for entry in friends:
            self.model.add_or_update_friend(
                entry.get("username", ""),
                status=entry.get("status", "OFFLINE"),
                in_voice=bool(entry.get("in_voice", False)),
            )
        self.friends_changed.emit()

    def _on_friend_request(self, sender: str) -> None:
        self.model.add_or_update_friend(sender, pending=True)
        self.friends_changed.emit()

    def _on_room_joined(self, room: str) -> None:
        self.model.add_or_update_room(room)
        self.rooms_changed.emit()

    def _on_room_left(self, room: str) -> None:
        self.rooms_changed.emit()

    def _on_room_deleted(self, room: str) -> None:
        self.model.remove_room(room)
        self.rooms_changed.emit()

    def _on_room_list(self, rooms: List[str]) -> None:
        for room in rooms:
            self.model.add_or_update_room(room)
        self.rooms_changed.emit()

    def _on_transfer_start(self, transfer_id: str, filename: str, filesize: int) -> None:
        self.model.add_file_transfer(transfer_id, filename, filesize)

    def _on_transfer_progress(self, transfer_id: str, progress: int) -> None:
        self.model.update_file_transfer_progress(transfer_id, progress)

    def _on_transfer_complete(self, transfer_id: str) -> None:
        self.model.complete_file_transfer(transfer_id)

    def _on_transfer_error(self, transfer_id: str, error: str) -> None:
        self.model.error_file_transfer(transfer_id, error)

    def _on_image_or_file(self, room_or_sender: str, filename: str, file_path: str) -> None:
        self.message_added.emit(room_or_sender)
