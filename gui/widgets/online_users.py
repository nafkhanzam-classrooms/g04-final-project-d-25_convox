"""Online users panel widget."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QLabel, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon

from gui.controllers.tcp_controller import TCPController
from utils.logger import get_logger


class OnlineUserPanel(QWidget):
    """Panel showing online users and friends."""

    user_clicked = pyqtSignal(str)  # username

    def __init__(self, tcp_controller: TCPController):
        super().__init__()
        self.logger = get_logger("OnlineUserPanel")
        self.tcp_controller = tcp_controller
        self.online_users = set()
        self.friends = {}

        self.init_ui()
        self.setMinimumWidth(200)
        self.setMaximumWidth(250)

    def init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget for users/friends
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: #ffffff;
                padding: 8px 15px;
                border-bottom: 2px solid #2b2b2b;
            }
            QTabBar::tab:selected {
                border-bottom: 2px solid #0078d4;
            }
        """)

        # Online users tab
        users_widget = QWidget()
        users_layout = QVBoxLayout()
        users_layout.setContentsMargins(0, 0, 0, 0)

        self.users_list = QListWidget()
        self.users_list.itemDoubleClicked.connect(self.on_user_double_clicked)
        self.users_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border: none;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        users_layout.addWidget(self.users_list)

        users_widget.setLayout(users_layout)
        self.tabs.addTab(users_widget, "Online")

        # Friends tab
        friends_widget = QWidget()
        friends_layout = QVBoxLayout()
        friends_layout.setContentsMargins(0, 0, 0, 0)

        self.friends_list = QListWidget()
        self.friends_list.itemDoubleClicked.connect(self.on_friend_double_clicked)
        self.friends_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border: none;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        friends_layout.addWidget(self.friends_list)

        friends_widget.setLayout(friends_layout)
        self.tabs.addTab(friends_widget, "Friends")

        layout.addWidget(self.tabs)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(10, 10, 10, 10)
        button_layout.setSpacing(5)

        add_friend_btn = QPushButton("+ Friend")
        add_friend_btn.setMinimumHeight(30)
        add_friend_btn.clicked.connect(self.add_friend_dialog)
        add_friend_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2fb34e;
            }
        """)
        button_layout.addWidget(add_friend_btn)

        msg_btn = QPushButton("Message")
        msg_btn.setMinimumHeight(30)
        msg_btn.clicked.connect(self.send_private_message)
        msg_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1084d7;
            }
        """)
        button_layout.addWidget(msg_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setStyleSheet("background-color: #2b2b2b;")

    def set_users(self, users: list) -> None:
        """Update online users list."""
        self.online_users = set(users)
        self.users_list.clear()

        for user in sorted(users):
            item = QListWidgetItem(f"● {user}")
            item.setData(Qt.ItemDataRole.UserRole, user)
            item.setForeground(QColor("#00d944"))  # Green
            self.users_list.addItem(item)

    def update_user(self, username: str, status: str) -> None:
        """Update single user status."""
        if status == "ONLINE":
            self.online_users.add(username)
            # Update display
            self.set_users(list(self.online_users))
        else:
            self.online_users.discard(username)
            self.set_users(list(self.online_users))

    def set_friends(self, friends: list) -> None:
        """Update friends list."""
        self.friends_list.clear()
        self.friends = {f["username"]: f for f in friends}

        for friend in sorted(friends, key=lambda x: x.get("username", "")):
            username = friend.get("username", "unknown")
            status = friend.get("status", "OFFLINE")
            online = status == "ONLINE"

            display_text = f"{'● ' if online else '○ '}{username}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, username)

            if online:
                item.setForeground(QColor("#00d944"))  # Green
            else:
                item.setForeground(QColor("#808080"))  # Gray

            self.friends_list.addItem(item)

    def on_user_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle user double click."""
        username = item.data(Qt.ItemDataRole.UserRole)
        self.user_clicked.emit(username)

    def on_friend_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle friend double click."""
        username = item.data(Qt.ItemDataRole.UserRole)
        self.user_clicked.emit(username)

    def add_friend_dialog(self) -> None:
        """Show add friend dialog."""
        from PyQt6.QtWidgets import QInputDialog
        username, ok = QInputDialog.getText(
            self,
            "Add Friend",
            "Username:"
        )
        if ok and username:
            self.tcp_controller.add_friend(username)

    def send_private_message(self) -> None:
        """Send private message to selected user."""
        current_item = self.users_list.currentItem() or self.friends_list.currentItem()
        if current_item:
            username = current_item.data(Qt.ItemDataRole.UserRole)
            self.logger.info("Private message to %s", username)
