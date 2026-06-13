"""Room sidebar widget."""

from typing import Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.controllers.event_dispatcher import get_dispatcher
from gui.controllers.tcp_controller import TCPController
from gui.models.app_model import ApplicationModel
from gui.styles import colors
from utils.logger import get_logger


class RoomSidebar(QWidget):
    """Left sidebar listing all known rooms."""

    room_changed = pyqtSignal(str)  # room name selected by the user

    def __init__(
        self,
        tcp_controller: TCPController,
        model: Optional[ApplicationModel] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.logger = get_logger("RoomSidebar")
        self.tcp_controller = tcp_controller
        self.dispatcher = get_dispatcher()
        self.model = model
        self.current_room = "global"
        self._items: Dict[str, QListWidgetItem] = {}
        self.setMinimumWidth(220)
        self.setMaximumWidth(280)
        self._build()
        self._wire_signals()
        self.add_room("global")

    # ---------------------------------------------------------------- layout
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet(
            f"background-color: {colors.BG_DEEPEST}; border-bottom: 1px solid {colors.BORDER_SOFT};"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 12, 0)
        title = QLabel("Rooms")
        title.setProperty("role", "section")
        title.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-weight: 700;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addWidget(header)

        self.room_list = QListWidget()
        self.room_list.itemClicked.connect(self._on_room_selected)
        layout.addWidget(self.room_list, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(10, 10, 10, 12)
        button_row.setSpacing(6)

        self.create_btn = QPushButton("+ New")
        self.create_btn.clicked.connect(self.create_room_dialog)
        button_row.addWidget(self.create_btn)

        self.join_btn = QPushButton("Join")
        self.join_btn.setProperty("variant", "subtle")
        self.join_btn.clicked.connect(self.join_room_dialog)
        button_row.addWidget(self.join_btn)

        layout.addLayout(button_row)

    # ---------------------------------------------------------------- signals
    def _wire_signals(self) -> None:
        self.dispatcher.room_joined.connect(self.add_room)
        self.dispatcher.room_deleted.connect(self.remove_room)
        self.dispatcher.room_list_updated.connect(self._on_room_list)
        self.dispatcher.session_restored.connect(lambda _u, room: self.set_current(room))

    # ----------------------------------------------------------------- public
    def add_room(self, room_name: str) -> None:
        if not room_name or room_name in self._items:
            return
        item = QListWidgetItem(self._format_label(room_name, 0))
        item.setData(Qt.ItemDataRole.UserRole, room_name)
        self.room_list.addItem(item)
        self._items[room_name] = item
        if room_name == self.current_room:
            self.room_list.setCurrentItem(item)

    def remove_room(self, room_name: str) -> None:
        item = self._items.pop(room_name, None)
        if item is not None:
            row = self.room_list.row(item)
            self.room_list.takeItem(row)
        if self.current_room == room_name:
            self.set_current("global")
            self.room_changed.emit("global")

    def set_current(self, room_name: str) -> None:
        self.add_room(room_name)
        self.current_room = room_name
        item = self._items.get(room_name)
        if item is not None:
            self.room_list.setCurrentItem(item)
            self._refresh_label(room_name)

    def update_room_unread(self, room_name: str) -> None:
        if self.model is None or room_name not in self.model.rooms:
            return
        self._refresh_label(room_name)

    def refresh_unread(self) -> None:
        if self.model is None:
            return
        for name in list(self._items.keys()):
            self._refresh_label(name)

    # -------------------------------------------------------------- internals
    def _on_room_selected(self, item: QListWidgetItem) -> None:
        room_name = item.data(Qt.ItemDataRole.UserRole)
        if not room_name or room_name == self.current_room:
            return
        self.current_room = room_name
        self.room_changed.emit(room_name)
        self._refresh_label(room_name)
        self.logger.info("Room selected: %s", room_name)

    def _on_room_list(self, rooms: list[str]) -> None:
        for name in rooms:
            self.add_room(name)

    def create_room_dialog(self) -> None:
        room_name, ok = QInputDialog.getText(self, "Create Room", "Room name:")
        if ok and room_name.strip():
            self.tcp_controller.create_room(room_name.strip())

    def join_room_dialog(self) -> None:
        room_name, ok = QInputDialog.getText(self, "Join Room", "Room name:")
        if ok and room_name.strip():
            self.tcp_controller.join_room(room_name.strip())
            self.add_room(room_name.strip())

    def _refresh_label(self, room_name: str) -> None:
        item = self._items.get(room_name)
        if item is None:
            return
        unread = 0
        if self.model is not None and room_name in self.model.rooms:
            unread = self.model.rooms[room_name].unread_count
        if room_name == self.current_room:
            unread = 0
            if self.model is not None and room_name in self.model.rooms:
                self.model.rooms[room_name].clear_unread()
        item.setText(self._format_label(room_name, unread))

    def _format_label(self, room_name: str, unread: int) -> str:
        prefix = "#"
        if unread > 0:
            return f"{prefix} {room_name}    ({unread})"
        return f"{prefix} {room_name}"
