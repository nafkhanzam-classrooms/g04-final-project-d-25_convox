"""Login window for the Convox desktop client."""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.controllers.event_dispatcher import get_dispatcher
from gui.controllers.tcp_controller import TCPController
from gui.styles import colors
from gui.windows.dashboard_window import DashboardWindow
from utils.logger import get_logger

try:
    from client.config import SERVER_HOST, SERVER_PORT
except ImportError:  # pragma: no cover - fallback for unusual layouts
    SERVER_HOST, SERVER_PORT = "127.0.0.1", 9000


class LoginWindow(QMainWindow):
    """Username + reconnect token entry window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.logger = get_logger("LoginWindow")
        self.tcp_controller = TCPController(host=SERVER_HOST, port=SERVER_PORT)
        self.dispatcher = get_dispatcher()
        self.dashboard: Optional[DashboardWindow] = None
        self.session_token: Optional[str] = None
        self._completed: bool = False

        self.setWindowTitle("Convox - Sign In")
        self.setFixedSize(440, 480)
        self._build()
        self._wire_signals()

    # ---------------------------------------------------------------- layout
    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(40, 36, 40, 36)
        outer.setSpacing(14)

        title = QLabel("CONVOX")
        title.setProperty("role", "title")
        font = QFont()
        font.setPointSize(28)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(title)

        subtitle = QLabel("Realtime Communication Platform")
        subtitle.setProperty("role", "subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(subtitle)

        outer.addSpacing(18)

        outer.addWidget(self._label("Username"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("e.g. fabian")
        self.username_input.returnPressed.connect(self.attempt_login)
        outer.addWidget(self.username_input)

        outer.addWidget(self._label("Session Token (optional)"))
        self.session_input = QLineEdit()
        self.session_input.setPlaceholderText("Paste a token here to reconnect to a previous session")
        self.session_input.setEchoMode(QLineEdit.EchoMode.Password)
        outer.addWidget(self.session_input)

        self.remember_checkbox = QCheckBox("Remember session token")
        outer.addWidget(self.remember_checkbox)

        outer.addSpacing(6)

        self.server_status = QLabel(f"Server: {SERVER_HOST}:{SERVER_PORT}  •  ready")
        self.server_status.setProperty("role", "muted")
        self.server_status.setStyleSheet(f"color: {colors.TEXT_MUTED};")
        self.server_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.server_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        outer.addWidget(self.progress_bar)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.login_button = QPushButton("Connect")
        self.login_button.setMinimumHeight(40)
        self.login_button.clicked.connect(self.attempt_login)
        button_row.addWidget(self.login_button)
        outer.addLayout(button_row)

        outer.addStretch(1)

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "section")
        label.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-weight: 600;")
        return label

    # ---------------------------------------------------------------- signals
    def _wire_signals(self) -> None:
        self.dispatcher.login_success.connect(self.on_login_success)
        self.dispatcher.login_failed.connect(self.on_login_failed)
        self.dispatcher.session_restored.connect(self.on_session_restored)
        self.dispatcher.connection_error.connect(self.on_connection_error)
        self.dispatcher.error.connect(self.on_error)

    # --------------------------------------------------------------- actions
    def attempt_login(self) -> None:
        username = self.username_input.text().strip()
        session_token = self.session_input.text().strip()

        if not username and not session_token:
            QMessageBox.warning(self, "Missing Information", "Please enter a username or session token.")
            return

        self.login_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.server_status.setText("Connecting…")
        self.tcp_controller.start()

        if session_token:
            self.session_token = session_token
            self.tcp_controller.reconnect(session_token)
        else:
            self.tcp_controller.login(username)

    # -------------------------------------------------------------- handlers
    def on_login_success(self, username: str) -> None:
        if self._completed:
            return
        self._completed = True
        if username:
            self.username_input.setText(username)
        self.logger.info("Login success for %s", username or "<unknown>")
        self.server_status.setText("Authenticated")
        QTimer.singleShot(400, self.open_dashboard)

    def on_session_restored(self, username: str, room: str) -> None:
        if self._completed:
            return
        self._completed = True
        if username:
            self.username_input.setText(username)
        self.logger.info("Session restored for %s in %s", username, room)
        self.server_status.setText(f"Reconnected to {room}")
        QTimer.singleShot(400, self.open_dashboard)

    def on_login_failed(self, message: str) -> None:
        self._reset_after_failure()
        QMessageBox.critical(self, "Login Failed", message)

    def on_connection_error(self, message: str) -> None:
        self._reset_after_failure()
        QMessageBox.critical(self, "Connection Error", message)

    def on_error(self, message: str) -> None:
        if self._completed:
            return
        self._reset_after_failure()
        QMessageBox.warning(self, "Server Message", message)

    def _reset_after_failure(self) -> None:
        self.progress_bar.setVisible(False)
        self.login_button.setEnabled(True)
        self.server_status.setText(f"Server: {SERVER_HOST}:{SERVER_PORT}  •  ready")
        # Stop the worker so the next attempt opens a fresh socket.
        self.tcp_controller.stop()

    def open_dashboard(self) -> None:
        username = self.username_input.text().strip() or "user"
        token = self.session_token or (
            self.tcp_controller.worker.session_token if self.tcp_controller.worker else None
        )
        self.dashboard = DashboardWindow(self.tcp_controller, username, token)
        self.dashboard.show()
        self.close()

    # --------------------------------------------------------------- close
    def closeEvent(self, event) -> None:
        if not self._completed:
            self.tcp_controller.stop()
        super().closeEvent(event)
