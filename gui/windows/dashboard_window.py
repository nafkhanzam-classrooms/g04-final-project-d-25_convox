"""Main Convox dashboard window."""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from gui.controllers.event_dispatcher import get_dispatcher
from gui.controllers.gui_state_manager import GuiStateManager
from gui.controllers.tcp_controller import TCPController
from gui.controllers.udp_voice_controller import UDPVoiceController
from gui.models.app_model import ApplicationModel
from gui.models.message_model import MessageKind
from gui.models.user_model import UserStatus
from gui.styles import colors
from gui.widgets.chat_area import ChatArea
from gui.widgets.notification_widget import NotificationWidget
from gui.widgets.online_users import OnlineUserPanel
from gui.widgets.room_sidebar import RoomSidebar
from gui.widgets.upload_widget import UploadWidget
from gui.widgets.voice_controls import VoiceControls
from utils.helper import timestamp as helper_timestamp
from utils.logger import get_logger

try:
    from client.config import SERVER_HOST
except ImportError:  # pragma: no cover
    SERVER_HOST = "127.0.0.1"

VOICE_UDP_PORT = 9001


class DashboardWindow(QMainWindow):
    """Main client window after authentication."""

    def __init__(
        self,
        tcp_controller: TCPController,
        username: str,
        session_token: Optional[str] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.logger = get_logger("DashboardWindow")
        self.tcp_controller = tcp_controller
        self.username = username
        self.session_token = session_token
        self.dispatcher = get_dispatcher()
        self.model = ApplicationModel()
        self.model.set_username(username)
        if session_token:
            self.model.set_session_token(session_token)

        self.state_manager = GuiStateManager(self.model, self.dispatcher)
        self.state_manager.set_identity(username, session_token)

        self.voice_controller = UDPVoiceController(
            username=username,
            server_host=SERVER_HOST,
            server_port=VOICE_UDP_PORT,
        )

        self.notifications = NotificationWidget()
        self.private_target: Optional[str] = None

        self.setWindowTitle(f"Convox - {username}")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 820)

        self._build()
        self._wire_signals()
        self._render_room()
        self._refresh_user_list()

        # Periodic refresh of presence/online lists
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_user_list)
        self._refresh_timer.start(8000)

        # Pull friends right away
        self.tcp_controller.get_friends()

    # ---------------------------------------------------------------- layout
    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        self.room_sidebar = RoomSidebar(self.tcp_controller, self.model)
        splitter.addWidget(self.room_sidebar)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.room_header = QLabel("# global")
        self.room_header.setFixedHeight(48)
        self.room_header.setContentsMargins(20, 0, 20, 0)
        self.room_header.setStyleSheet(
            f"background-color: {colors.BG_DEEPEST}; color: {colors.TEXT_PRIMARY}; "
            f"font-size: 15px; font-weight: 700; border-bottom: 1px solid {colors.BORDER_SOFT};"
        )
        center_layout.addWidget(self.room_header)

        self.chat_area = ChatArea()
        center_layout.addWidget(self.chat_area, 1)

        center_layout.addLayout(self._build_input_row())
        splitter.addWidget(center)

        self.online_users_panel = OnlineUserPanel(self.tcp_controller, self.model)
        splitter.addWidget(self.online_users_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([240, 760, 280])
        root.addWidget(splitter, 1)

        self.voice_controls = VoiceControls(self.tcp_controller, self.voice_controller)
        root.addWidget(self.voice_controls)

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setObjectName("topbar")
        bar.setStyleSheet(
            f"#topbar {{ background-color: {colors.BG_DEEPEST}; "
            f"border-bottom: 1px solid {colors.BORDER_SOFT}; }}"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        brand = QLabel("CONVOX")
        brand.setStyleSheet(
            f"color: {colors.TEXT_PRIMARY}; font-weight: 800; letter-spacing: 1px;"
        )
        layout.addWidget(brand)

        layout.addSpacing(16)

        self.user_label = QLabel(f"{self.username}")
        self.user_label.setStyleSheet(f"color: {colors.TEXT_SECONDARY};")
        layout.addWidget(self.user_label)

        layout.addStretch(1)

        self.status_button = QPushButton("● Online")
        self.status_button.setProperty("variant", "ghost")
        self.status_button.setStyleSheet(
            f"QPushButton {{ color: {colors.STATUS_ONLINE}; "
            f"border: 1px solid {colors.BORDER_STRONG}; border-radius: 6px; padding: 4px 12px; }}"
            f"QPushButton:hover {{ background-color: {colors.BG_ELEVATED}; }}"
        )
        self.status_button.clicked.connect(self._show_status_menu)
        layout.addWidget(self.status_button)

        if self.session_token:
            copy_token = QPushButton("Copy Session Token")
            copy_token.setProperty("variant", "ghost")
            copy_token.clicked.connect(self._copy_session_token)
            layout.addWidget(copy_token)

        disconnect = QPushButton("Disconnect")
        disconnect.setProperty("variant", "danger")
        disconnect.clicked.connect(self.disconnect)
        layout.addWidget(disconnect)

        return bar

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(16, 12, 16, 14)
        row.setSpacing(8)

        self.upload_widget = UploadWidget(self.tcp_controller)
        self.upload_widget.file_selected.connect(self._on_file_selected)
        row.addWidget(self.upload_widget)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Message #global  (Enter to send)")
        self.message_input.setMinimumHeight(40)
        self.message_input.returnPressed.connect(self.send_message)
        row.addWidget(self.message_input, 1)

        self.cancel_private_btn = QPushButton("Cancel DM")
        self.cancel_private_btn.setProperty("variant", "subtle")
        self.cancel_private_btn.setVisible(False)
        self.cancel_private_btn.clicked.connect(self._exit_private_mode)
        row.addWidget(self.cancel_private_btn)

        send_btn = QPushButton("Send")
        send_btn.setMinimumHeight(40)
        send_btn.clicked.connect(self.send_message)
        row.addWidget(send_btn)
        return row

    # ---------------------------------------------------------------- signals
    def _wire_signals(self) -> None:
        self.dispatcher.session_restored.connect(self._on_session_restored)
        self.dispatcher.system_message.connect(self._on_system_message)
        self.dispatcher.private_message_received.connect(self._on_private_message)
        self.dispatcher.friend_request_received.connect(self._on_friend_request)
        self.dispatcher.image_received.connect(self._on_image_received)
        self.dispatcher.error.connect(self._on_error)
        self.dispatcher.connection_error.connect(self._on_error)
        self.dispatcher.disconnected.connect(self._on_disconnected)

        self.state_manager.message_added.connect(self._on_message_added)
        self.state_manager.rooms_changed.connect(self._on_rooms_changed)
        self.state_manager.users_changed.connect(self.online_users_panel.refresh)
        self.state_manager.friends_changed.connect(self.online_users_panel.refresh)

        self.room_sidebar.room_changed.connect(self._on_room_changed)
        self.online_users_panel.private_message_requested.connect(self._enter_private_mode)

    # ---------------------------------------------------------------- actions
    def send_message(self) -> None:
        text = self.message_input.text().strip()
        if not text:
            return

        if self.private_target:
            self.tcp_controller.send_private_message(self.private_target, text)
            # Private messages are not echoed back by the server, so we
            # display them locally for immediate feedback.
            self.state_manager.record_outgoing_private(
                self.private_target, text, helper_timestamp()
            )
        else:
            room = self.room_sidebar.current_room
            self.tcp_controller.send_message(room, text)
            # Room messages ARE echoed back via the MESSAGE packet, so we
            # let the dispatcher draw them once the server confirms.
        self.message_input.clear()

    def disconnect(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Disconnect",
            "Disconnect from the server?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._cleanup()
        self.close()

    # -------------------------------------------------------------- handlers
    def _on_session_restored(self, username: str, room: str) -> None:
        self.username = username or self.username
        self.user_label.setText(self.username)
        if room:
            self.room_sidebar.set_current(room)

    def _on_message_added(self, target: str) -> None:
        if target.startswith("@"):
            other = target[1:]
            if self.private_target and other == self.private_target:
                self._render_private(other)
            else:
                self.notifications.show_notification(
                    "Private message",
                    f"New DM from {other}. Double-click them in the user list to reply.",
                )
            return
        if target == self.room_sidebar.current_room:
            self._render_room()
        else:
            self.room_sidebar.update_room_unread(target)

    def _on_rooms_changed(self) -> None:
        self.room_sidebar.refresh_unread()

    def _on_room_changed(self, room_name: str) -> None:
        if self.private_target:
            self._exit_private_mode()
        self.state_manager.set_current_room(room_name)
        self.tcp_controller.join_room(room_name)
        self.voice_controls.set_room(room_name)
        self._render_room()

    def _on_system_message(self, room: str, message: str) -> None:
        if room == self.room_sidebar.current_room:
            return  # Already handled by state-manager / chat re-render
        self.notifications.show_notification(f"# {room}", message)

    def _on_private_message(self, sender: str, _msg: str, _ts: str) -> None:
        if not self.private_target or sender != self.private_target:
            self.notifications.show_notification(f"DM from {sender}", _msg or "")

    def _on_friend_request(self, from_user: str) -> None:
        self.notifications.show_notification(
            "Friend Request",
            f"{from_user} sent you a friend request",
        )

    def _on_image_received(self, room_or_sender: str, filename: str, _path: str) -> None:
        self.notifications.show_notification(
            "File received",
            f"{filename} (in {room_or_sender})",
        )

    def _on_error(self, message: str) -> None:
        self.logger.error("Error: %s", message)
        self.notifications.show_notification("Error", message)

    def _on_disconnected(self) -> None:
        self.notifications.show_notification("Disconnected", "Lost connection to the Convox server.")

    def _on_file_selected(self, path: str) -> None:
        # Phase 1 GUI surfaces uploads through the controller. Backend
        # already supports image/file packets via the terminal client, so
        # the GUI simply forwards the choice as a notification for now.
        self.notifications.show_notification(
            "File queued",
            f"{path}\nUpload via terminal client; GUI upload pipeline is wired for status only.",
        )

    # ----------------------------------------------------------------- helpers
    def _render_room(self) -> None:
        room = self.room_sidebar.current_room
        self.room_header.setText(f"# {room}")
        self.message_input.setPlaceholderText(f"Message #{room}  (Enter to send)")
        messages = self.model.get_room_messages(room)
        self.chat_area.render_messages(messages)
        if room in self.model.rooms:
            self.model.rooms[room].clear_unread()
            self.room_sidebar.update_room_unread(room)

    def _render_private(self, other: str) -> None:
        # Rebuild bubble list with all DM messages between us and ``other``.
        msgs = [
            m for m in self.model.messages
            if m.kind == MessageKind.PRIVATE
            and (m.sender == other or m.target_user == other)
            or (m.kind == MessageKind.SELF and m.target_user == other)
        ]
        self.chat_area.render_messages(msgs)

    def _refresh_user_list(self) -> None:
        self.tcp_controller.get_online_users()

    def _enter_private_mode(self, target: str) -> None:
        if not target:
            return
        self.private_target = target
        self.room_header.setText(f"@ {target}  (private)")
        self.message_input.setPlaceholderText(f"Message @{target}  (Enter to send)")
        self.cancel_private_btn.setVisible(True)
        self._render_private(target)

    def _exit_private_mode(self) -> None:
        self.private_target = None
        self.cancel_private_btn.setVisible(False)
        self._render_room()

    # ----------------------------------------------------------------- status
    def _show_status_menu(self) -> None:
        menu = QMenu(self)
        for status in (UserStatus.ONLINE, UserStatus.IN_ROOM, UserStatus.DO_NOT_DISTURB):
            action = QAction(status.value, menu)
            action.triggered.connect(lambda _checked, s=status: self._set_status(s))
            menu.addAction(action)
        menu.exec(self.status_button.mapToGlobal(self.status_button.rect().bottomLeft()))

    def _set_status(self, status: UserStatus) -> None:
        self.tcp_controller.update_status(status.value)
        self.state_manager.set_status(status.value)
        color = colors.status_color(status.value)
        self.status_button.setText(f"● {status.value.replace('_', ' ').title()}")
        self.status_button.setStyleSheet(
            f"QPushButton {{ color: {color}; "
            f"border: 1px solid {colors.BORDER_STRONG}; border-radius: 6px; padding: 4px 12px; }}"
            f"QPushButton:hover {{ background-color: {colors.BG_ELEVATED}; }}"
        )

    def _copy_session_token(self) -> None:
        if not self.session_token:
            return
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.session_token)
        self.notifications.show_notification(
            "Session token copied",
            "Paste it on the login screen next time to reconnect.",
        )

    # ------------------------------------------------------------------ close
    def _cleanup(self) -> None:
        try:
            self._refresh_timer.stop()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.voice_controller.leave()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.tcp_controller.stop()
        except Exception:  # noqa: BLE001
            pass

    def closeEvent(self, event) -> None:
        self._cleanup()
        super().closeEvent(event)
