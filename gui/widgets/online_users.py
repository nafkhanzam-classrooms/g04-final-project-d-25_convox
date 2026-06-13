"""Online users + friends panel."""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.controllers.event_dispatcher import get_dispatcher
from gui.controllers.tcp_controller import TCPController
from gui.models.app_model import ApplicationModel
from gui.models.user_model import UserStatus
from gui.styles import colors
from gui.widgets.friend_panel import FriendPanel
from utils.logger import get_logger


class OnlineUserPanel(QWidget):
    """Right-hand panel: online users in one tab, friends in another."""

    user_clicked = pyqtSignal(str)              # username double-click on online list
    private_message_requested = pyqtSignal(str)

    def __init__(
        self,
        tcp_controller: TCPController,
        model: ApplicationModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.logger = get_logger("OnlineUserPanel")
        self.tcp_controller = tcp_controller
        self.dispatcher = get_dispatcher()
        self.model = model
        self.setMinimumWidth(220)
        self.setMaximumWidth(300)
        self._build()
        self._wire_signals()

    # ---------------------------------------------------------------- layout
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Online users tab
        online_widget = QWidget()
        online_layout = QVBoxLayout(online_widget)
        online_layout.setContentsMargins(0, 6, 0, 6)
        online_layout.setSpacing(4)
        self.users_list = QListWidget()
        self.users_list.itemDoubleClicked.connect(self._on_user_double_clicked)
        online_layout.addWidget(self.users_list, 1)
        self.tabs.addTab(online_widget, "Online")

        # Friends tab
        self.friend_panel = FriendPanel(self.tcp_controller, self.model)
        self.friend_panel.friend_message_requested.connect(self.private_message_requested)
        self.tabs.addTab(self.friend_panel, "Friends")

    def _wire_signals(self) -> None:
        self.dispatcher.online_users_updated.connect(self._on_online_users)
        self.dispatcher.user_status_changed.connect(lambda _u, _s: self._render_users())

    # ----------------------------------------------------------------- public
    def refresh(self) -> None:
        self._render_users()
        self.friend_panel.refresh()

    # Compatibility entrypoints used by older callers ------------------------
    def set_users(self, users: list[str]) -> None:
        for user in users:
            self.model.add_or_update_user(user, status="ONLINE")
        seen = set(users)
        for username, user in list(self.model.users.items()):
            if username not in seen and username != self.model.username:
                user.status = UserStatus.OFFLINE
        self._render_users()

    def update_user(self, username: str, status: str) -> None:
        self.model.add_or_update_user(username, status=status)
        self._render_users()

    def set_friends(self, friends: list[dict]) -> None:
        self.model.friends.clear()
        for entry in friends:
            self.model.add_or_update_friend(
                entry.get("username", ""),
                status=entry.get("status", "OFFLINE"),
                in_voice=bool(entry.get("in_voice", False)),
            )
        self.friend_panel.refresh()

    # -------------------------------------------------------------- handlers
    def _on_online_users(self, users: list[str]) -> None:
        # State manager already updated the model, just re-render.
        self._render_users()

    def _render_users(self) -> None:
        self.users_list.clear()
        sorted_users = sorted(
            (u for u in self.model.users.values() if u.status != UserStatus.OFFLINE),
            key=lambda u: u.username.lower(),
        )
        for user in sorted_users:
            indicator = "🎙" if user.in_voice else "●"
            item = QListWidgetItem(f"{indicator} {user.username}")
            item.setData(Qt.ItemDataRole.UserRole, user.username)
            item.setForeground(QColor(colors.status_color(user.status.value)))
            self.users_list.addItem(item)

    def _on_user_double_clicked(self, item: QListWidgetItem) -> None:
        username = item.data(Qt.ItemDataRole.UserRole)
        if username:
            self.user_clicked.emit(username)
            self.private_message_requested.emit(username)
