"""Main dashboard window for Convox."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QPushButton, QLineEdit, QLabel, QMessageBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon

from gui.controllers.tcp_controller import TCPController
from gui.controllers.event_dispatcher import get_dispatcher
from gui.models.app_model import ApplicationModel, UserStatus
from gui.widgets.room_sidebar import RoomSidebar
from gui.widgets.chat_area import ChatArea
from gui.widgets.online_users import OnlineUserPanel
from gui.widgets.voice_controls import VoiceControls
from gui.widgets.notification_widget import NotificationWidget
from utils.logger import get_logger


class DashboardWindow(QMainWindow):
    """Main dashboard window after login."""

    def __init__(self, tcp_controller: TCPController, username: str, session_token: str = None):
        super().__init__()
        self.logger = get_logger("DashboardWindow")
        self.tcp_controller = tcp_controller
        self.username = username
        self.session_token = session_token
        self.dispatcher = get_dispatcher()
        self.model = ApplicationModel()
        self.model.set_username(username)
        if session_token:
            self.model.set_session_token(session_token)

        self.init_ui()
        self.connect_signals()
        self.start_background_tasks()

        self.setWindowTitle(f"Convox - {username}")
        self.setGeometry(100, 100, 1200, 800)
        self.show()

    def init_ui(self) -> None:
        """Initialize UI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top info bar
        info_bar = self.create_info_bar()
        main_layout.addWidget(info_bar)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left sidebar - rooms
        self.room_sidebar = RoomSidebar(self.tcp_controller)
        splitter.addWidget(self.room_sidebar)

        # Center - chat area
        center_layout = QVBoxLayout()
        center_widget = QWidget()

        self.chat_area = ChatArea()
        center_layout.addWidget(self.chat_area)

        # Input area
        input_layout = self.create_input_area()
        center_layout.addLayout(input_layout)

        center_widget.setLayout(center_layout)
        splitter.addWidget(center_widget)

        # Right sidebar - users and friends
        self.online_users_panel = OnlineUserPanel(self.tcp_controller)
        splitter.addWidget(self.online_users_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 1)

        main_layout.addWidget(splitter)

        # Bottom - voice controls
        voice_layout = QHBoxLayout()
        self.voice_controls = VoiceControls(self.tcp_controller)
        voice_layout.addWidget(self.voice_controls)
        main_layout.addLayout(voice_layout)

        central_widget.setLayout(main_layout)

        # Notification system
        self.notification_widget = NotificationWidget()
        self.notification_widget.show()

        # Apply styling
        self.apply_styling()

    def create_info_bar(self) -> QWidget:
        """Create top info bar."""
        widget = QWidget()
        widget.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #404040;")
        widget.setMaximumHeight(40)

        layout = QHBoxLayout()
        layout.setContentsMargins(15, 5, 15, 5)

        status_label = QLabel(f"User: {self.username}")
        status_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        layout.addWidget(status_label)

        self.status_combo = QPushButton("● Online")
        self.status_combo.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                color: #00d944;
                border: 1px solid #404040;
                border-radius: 3px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)
        self.status_combo.clicked.connect(self.show_status_menu)
        layout.addWidget(self.status_combo)

        layout.addStretch()

        disconnect_btn = QPushButton("Disconnect")
        disconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #c41e3a;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 3px 10px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        disconnect_btn.clicked.connect(self.disconnect)
        layout.addWidget(disconnect_btn)

        widget.setLayout(layout)
        return widget

    def create_input_area(self) -> QHBoxLayout:
        """Create message input area."""
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message... (Enter to send)")
        self.message_input.returnPressed.connect(self.send_message)
        self.message_input.setMinimumHeight(35)
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
        """)
        layout.addWidget(self.message_input)

        send_btn = QPushButton("Send")
        send_btn.setMinimumHeight(35)
        send_btn.setMaximumWidth(100)
        send_btn.clicked.connect(self.send_message)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d7;
            }
        """)
        layout.addWidget(send_btn)

        return layout

    def connect_signals(self) -> None:
        """Connect event signals."""
        self.dispatcher.message_received.connect(self.on_message_received)
        self.dispatcher.system_message.connect(self.on_system_message)
        self.dispatcher.private_message_received.connect(self.on_private_message)
        self.dispatcher.user_status_changed.connect(self.on_user_status_changed)
        self.dispatcher.online_users_updated.connect(self.on_online_users_updated)
        self.dispatcher.friend_request_received.connect(self.on_friend_request_received)
        self.dispatcher.room_joined.connect(self.on_room_joined)
        self.dispatcher.error.connect(self.on_error)

        self.room_sidebar.room_changed.connect(self.on_room_changed)
        self.online_users_panel.user_clicked.connect(self.on_user_clicked)

    def start_background_tasks(self) -> None:
        """Start background update tasks."""
        # Request online users periodically
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_user_lists)
        self.refresh_timer.start(5000)  # Every 5 seconds

    def on_message_received(self, room: str, sender: str, message: str, timestamp: str) -> None:
        """Handle incoming message."""
        self.model.add_message(sender, message, timestamp, room=room)
        if room == self.room_sidebar.current_room:
            self.chat_area.add_message(sender, message, timestamp)
        else:
            # Unread indicator
            if room in self.model.rooms:
                self.model.rooms[room].unread_count += 1
                self.room_sidebar.update_room_unread(room)

    def on_private_message(self, sender: str, message: str, timestamp: str) -> None:
        """Handle private message."""
        self.model.add_message(sender, message, timestamp, target_user=self.username)
        self.chat_area.add_message(f"[PRIVATE] {sender}", message, timestamp)
        self.notification_widget.show_notification(f"Private message from {sender}", message)

    def on_system_message(self, room: str, message: str) -> None:
        """Handle system message."""
        self.model.add_message("SYSTEM", message, "", room=room, is_system=True)
        if room == self.room_sidebar.current_room:
            self.chat_area.add_system_message(message)

    def on_user_status_changed(self, username: str, status: str) -> None:
        """Handle user status change."""
        self.model.add_or_update_user(username, status)
        self.online_users_panel.update_user(username, status)

    def on_online_users_updated(self, users: list) -> None:
        """Handle online users list update."""
        for user in users:
            self.model.add_or_update_user(user)
        self.online_users_panel.set_users(users)

    def on_friend_request_received(self, from_user: str) -> None:
        """Handle incoming friend request."""
        self.notification_widget.show_notification(
            f"Friend Request",
            f"{from_user} sent you a friend request"
        )

    def on_room_changed(self, room_name: str) -> None:
        """Handle room switch."""
        self.model.current_room = room_name
        self.chat_area.clear()
        messages = self.model.get_room_messages(room_name)
        for msg in messages:
            if msg.is_system:
                self.chat_area.add_system_message(msg.content)
            else:
                self.chat_area.add_message(msg.sender, msg.content, msg.timestamp)
        self.model.rooms[room_name].clear_unread()
        self.tcp_controller.join_room(room_name)

    def on_room_joined(self, room_name: str) -> None:
        """Handle successful room join."""
        self.room_sidebar.add_room(room_name)

    def on_user_clicked(self, username: str) -> None:
        """Handle user click in user panel."""
        reply = QMessageBox.question(
            self,
            f"Action for {username}",
            f"What would you like to do?",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )

    def on_error(self, error_message: str) -> None:
        """Handle errors."""
        self.logger.error("Error: %s", error_message)
        self.notification_widget.show_notification("Error", error_message)

    def send_message(self) -> None:
        """Send chat message."""
        message = self.message_input.text().strip()
        if not message:
            return

        room = self.room_sidebar.current_room
        self.tcp_controller.send_message(room, message)
        self.chat_area.add_message(self.username, message, "now")
        self.message_input.clear()

    def refresh_user_lists(self) -> None:
        """Refresh online users and friends."""
        self.tcp_controller.get_online_users()

    def show_status_menu(self) -> None:
        """Show status change menu."""
        pass  # Placeholder for status menu

    def disconnect(self) -> None:
        """Disconnect and close application."""
        reply = QMessageBox.question(
            self,
            "Disconnect",
            "Are you sure you want to disconnect?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.tcp_controller.stop()
            self.close()

    def apply_styling(self) -> None:
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
            }
        """)

    def closeEvent(self, event) -> None:
        """Clean up on window close."""
        self.refresh_timer.stop()
        self.tcp_controller.stop()
        super().closeEvent(event)
