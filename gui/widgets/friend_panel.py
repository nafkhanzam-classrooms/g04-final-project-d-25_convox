"""Friend list panel widget."""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
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


class FriendPanel(QWidget):
    """Friend list with shortcuts to add / message / accept-reject friends."""

    friend_message_requested = pyqtSignal(str)  # username
    friend_added = pyqtSignal(str)              # username

    def __init__(
        self,
        tcp_controller: TCPController,
        model: ApplicationModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.logger = get_logger("FriendPanel")
        self.tcp_controller = tcp_controller
        self.dispatcher = get_dispatcher()
        self.model = model

        self._build()
        self._wire_signals()
        self.refresh()

    # ---------------------------------------------------------------- layout
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(6)

        title = QLabel("Friends")
        title.setProperty("role", "section")
        title.setContentsMargins(12, 0, 12, 0)
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_widget, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(10, 0, 10, 0)
        button_row.setSpacing(6)

        self.add_btn = QPushButton("+ Add")
        self.add_btn.setProperty("variant", "success")
        self.add_btn.clicked.connect(self._add_dialog)
        button_row.addWidget(self.add_btn)

        self.message_btn = QPushButton("Message")
        self.message_btn.clicked.connect(self._message_selected)
        button_row.addWidget(self.message_btn)

        self.accept_btn = QPushButton("Accept")
        self.accept_btn.setProperty("variant", "subtle")
        self.accept_btn.clicked.connect(self._accept_selected)
        button_row.addWidget(self.accept_btn)

        layout.addLayout(button_row)

    def _wire_signals(self) -> None:
        self.dispatcher.friend_list_updated.connect(lambda _: self.refresh())
        self.dispatcher.friend_request_received.connect(lambda _: self.refresh())
        self.dispatcher.user_status_changed.connect(lambda _u, _s: self.refresh())

    # ----------------------------------------------------------------- public
    def refresh(self) -> None:
        self.list_widget.clear()
        for friend in sorted(self.model.friends.values(), key=lambda f: (not f.pending, f.username)):
            label = self._format(friend)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, friend.username)
            item.setForeground(QColor(colors.status_color(friend.status.value)))
            self.list_widget.addItem(item)

    def _format(self, friend) -> str:
        prefix = "● "
        if friend.pending:
            prefix = "✉ "
        elif friend.in_voice:
            prefix = "🎙 "
        elif friend.status.value == "OFFLINE":
            prefix = "○ "
        suffix = "  (pending)" if friend.pending else ""
        return f"{prefix}{friend.username}{suffix}"

    # -------------------------------------------------------------- handlers
    def _on_double_click(self, item: QListWidgetItem) -> None:
        username = item.data(Qt.ItemDataRole.UserRole)
        friend = self.model.friends.get(username)
        if friend and friend.pending:
            self.tcp_controller.accept_friend(username)
            return
        self.friend_message_requested.emit(username)

    def _add_dialog(self) -> None:
        username, ok = QInputDialog.getText(self, "Add Friend", "Username:")
        if ok and username.strip():
            target = username.strip()
            self.tcp_controller.add_friend(target)
            self.friend_added.emit(target)

    def _message_selected(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        self.friend_message_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _accept_selected(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        username = item.data(Qt.ItemDataRole.UserRole)
        friend = self.model.friends.get(username)
        if friend and friend.pending:
            self.tcp_controller.accept_friend(username)
