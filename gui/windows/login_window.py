"""Login window for the Convox desktop client."""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
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
except ImportError:  # pragma: no cover
    SERVER_HOST, SERVER_PORT = "127.0.0.1", 9000


# UI mode constants
_MODE_LOGIN = 0
_MODE_REGISTER = 1
_MODE_RECONNECT = 2


class LoginWindow(QMainWindow):
    """Sign-in / sign-up / reconnect entry point.

    The window owns a single ``TCPController`` for the lifetime of the
    auth handshake and hands it off to the dashboard once login succeeds.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.logger = get_logger("LoginWindow")
        self.tcp_controller = TCPController(host=SERVER_HOST, port=SERVER_PORT)
        self.dispatcher = get_dispatcher()
        self.dashboard: Optional[DashboardWindow] = None
        self.session_token: Optional[str] = None
        self._completed: bool = False
        self._mode: int = _MODE_LOGIN
        self._busy: bool = False

        self.setWindowTitle("Convox - Sign In")
        self.setFixedSize(460, 560)
        self._build()
        self._wire_signals()
        self._show_mode(_MODE_LOGIN)

    # ---------------------------------------------------------------- layout
    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(40, 30, 40, 30)
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

        outer.addSpacing(8)

        # Mode toggle row
        toggle = QHBoxLayout()
        toggle.setSpacing(0)
        self.tab_login = self._make_tab("Sign In", _MODE_LOGIN)
        self.tab_register = self._make_tab("Sign Up", _MODE_REGISTER)
        self.tab_reconnect = self._make_tab("Reconnect", _MODE_RECONNECT)
        toggle.addWidget(self.tab_login)
        toggle.addWidget(self.tab_register)
        toggle.addWidget(self.tab_reconnect)
        outer.addLayout(toggle)

        outer.addSpacing(6)

        # Stacked panels for each mode
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_login_panel())
        self.stack.addWidget(self._build_register_panel())
        self.stack.addWidget(self._build_reconnect_panel())
        outer.addWidget(self.stack, 1)

        self.server_status = QLabel(f"Server: {SERVER_HOST}:{SERVER_PORT}  •  ready")
        self.server_status.setStyleSheet(f"color: {colors.TEXT_MUTED};")
        self.server_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.server_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        outer.addWidget(self.progress_bar)

        self.submit_button = QPushButton("Sign In")
        self.submit_button.setMinimumHeight(42)
        self.submit_button.clicked.connect(self._on_submit)
        outer.addWidget(self.submit_button)

    def _make_tab(self, label: str, mode: int) -> QPushButton:
        button = QPushButton(label)
        button.setCheckable(True)
        button.setProperty("variant", "ghost")
        button.setMinimumHeight(36)
        button.clicked.connect(lambda: self._show_mode(mode))
        return button

    def _build_login_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self._field_label("Username"))
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("e.g. fabian")
        self.login_username.returnPressed.connect(self._on_submit)
        layout.addWidget(self.login_username)

        layout.addWidget(self._field_label("Password"))
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Your password")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.returnPressed.connect(self._on_submit)
        layout.addWidget(self.login_password)

        layout.addStretch(1)
        return panel

    def _build_register_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self._field_label("Username"))
        self.register_username = QLineEdit()
        self.register_username.setPlaceholderText("3-32 chars: letters, digits, _ - .")
        self.register_username.returnPressed.connect(self._on_submit)
        layout.addWidget(self.register_username)

        layout.addWidget(self._field_label("Password"))
        self.register_password = QLineEdit()
        self.register_password.setPlaceholderText("At least 6 characters")
        self.register_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.register_password)

        layout.addWidget(self._field_label("Confirm Password"))
        self.register_password_confirm = QLineEdit()
        self.register_password_confirm.setPlaceholderText("Repeat password")
        self.register_password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_password_confirm.returnPressed.connect(self._on_submit)
        layout.addWidget(self.register_password_confirm)

        layout.addStretch(1)
        return panel

    def _build_reconnect_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self._field_label("Session Token"))
        self.reconnect_token = QLineEdit()
        self.reconnect_token.setPlaceholderText("Paste a session token from your previous login")
        self.reconnect_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.reconnect_token.returnPressed.connect(self._on_submit)
        layout.addWidget(self.reconnect_token)

        hint = QLabel(
            "Tip: copy the token from the dashboard's top bar after you sign in. "
            "Tokens stay valid for 15 minutes after disconnect."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {colors.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(hint)

        layout.addStretch(1)
        return panel

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "section")
        label.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-weight: 600;")
        return label

    # ---------------------------------------------------------------- signals
    def _wire_signals(self) -> None:
        self.dispatcher.login_success.connect(self.on_login_success)
        self.dispatcher.login_failed.connect(self.on_login_failed)
        self.dispatcher.register_success.connect(self.on_register_success)
        self.dispatcher.session_restored.connect(self.on_session_restored)
        self.dispatcher.connection_error.connect(self.on_connection_error)
        self.dispatcher.error.connect(self.on_error)
        self.dispatcher.disconnected.connect(self._on_disconnected)

    # --------------------------------------------------------------- mode
    def _show_mode(self, mode: int) -> None:
        self._mode = mode
        self.stack.setCurrentIndex(mode)
        self.tab_login.setChecked(mode == _MODE_LOGIN)
        self.tab_register.setChecked(mode == _MODE_REGISTER)
        self.tab_reconnect.setChecked(mode == _MODE_RECONNECT)
        self.submit_button.setText(
            {
                _MODE_LOGIN: "Sign In",
                _MODE_REGISTER: "Create Account",
                _MODE_RECONNECT: "Reconnect",
            }[mode]
        )

    # --------------------------------------------------------------- actions
    def _on_submit(self) -> None:
        if self._busy:
            return
        if self._mode == _MODE_LOGIN:
            self._submit_login()
        elif self._mode == _MODE_REGISTER:
            self._submit_register()
        else:
            self._submit_reconnect()

    def _submit_login(self) -> None:
        username = self.login_username.text().strip()
        password = self.login_password.text()
        if not username or not password:
            QMessageBox.warning(self, "Missing Information", "Username and password are required.")
            return
        self._begin_request("Signing in…")
        self.tcp_controller.start()
        self.tcp_controller.login(username, password)

    def _submit_register(self) -> None:
        username = self.register_username.text().strip()
        password = self.register_password.text()
        confirm = self.register_password_confirm.text()
        if not username or not password:
            QMessageBox.warning(self, "Missing Information", "Username and password are required.")
            return
        if password != confirm:
            QMessageBox.warning(self, "Passwords don't match", "Please re-enter your password.")
            return
        self._begin_request("Creating account…")
        self.tcp_controller.start()
        self.tcp_controller.register_account(username, password)

    def _submit_reconnect(self) -> None:
        token = self.reconnect_token.text().strip()
        if not token:
            QMessageBox.warning(self, "Missing Token", "Paste a session token to reconnect.")
            return
        self.session_token = token
        self._begin_request("Reconnecting…")
        self.tcp_controller.start()
        self.tcp_controller.reconnect(token)

    def _begin_request(self, status: str) -> None:
        self._busy = True
        self.submit_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.server_status.setText(status)

    def _end_request(self, status: str) -> None:
        self._busy = False
        self.submit_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.server_status.setText(status)

    # -------------------------------------------------------------- handlers
    def on_login_success(self, username: str) -> None:
        if self._completed:
            return
        self._completed = True
        if username:
            self.login_username.setText(username)
        self.logger.info("Login success for %s", username or "<unknown>")
        self.server_status.setText("Authenticated")
        self.progress_bar.setVisible(False)
        QTimer.singleShot(400, self.open_dashboard)

    def on_register_success(self, username: str) -> None:
        # Pop a confirmation, prefill the login form, switch to Sign In.
        self._end_request("Account created. Please sign in.")
        self.logger.info("Registered new account: %s", username)
        QMessageBox.information(
            self,
            "Account Created",
            f"Account '{username}' created. You can now sign in with your password.",
        )
        if self.register_username.text().strip():
            self.login_username.setText(self.register_username.text().strip())
        self.register_password.clear()
        self.register_password_confirm.clear()
        self._show_mode(_MODE_LOGIN)
        self.login_password.setFocus()

    def on_session_restored(self, username: str, room: str) -> None:
        if self._completed:
            return
        self._completed = True
        if username:
            self.login_username.setText(username)
        self.logger.info("Session restored for %s in %s", username, room)
        self.server_status.setText(f"Reconnected to {room}")
        self.progress_bar.setVisible(False)
        QTimer.singleShot(400, self.open_dashboard)

    def on_login_failed(self, message: str) -> None:
        if self._completed:
            return
        self._reset_after_failure()
        QMessageBox.critical(
            self,
            "Sign In Failed" if self._mode == _MODE_LOGIN else "Action Failed",
            message,
        )

    def on_connection_error(self, message: str) -> None:
        if self._completed:
            return
        self._reset_after_failure()
        QMessageBox.critical(self, "Connection Error", message)

    def on_error(self, message: str) -> None:
        if self._completed:
            return
        self._reset_after_failure()
        QMessageBox.warning(self, "Server Message", message)

    def _on_disconnected(self) -> None:
        if self._completed:
            return
        # Allow next attempt without leaving the user stuck on a spinner.
        self._end_request(f"Server: {SERVER_HOST}:{SERVER_PORT}  •  ready")

    def _reset_after_failure(self) -> None:
        self._end_request(f"Server: {SERVER_HOST}:{SERVER_PORT}  •  ready")
        # Stop the worker so the next attempt opens a fresh socket. The
        # server closes the connection after AUTH_FAILED, but stopping
        # here also handles the case where the server is unreachable.
        self.tcp_controller.stop()

    def open_dashboard(self) -> None:
        username = self.login_username.text().strip() or "user"
        token = self.session_token
        if not token and self.tcp_controller.worker:
            token = self.tcp_controller.worker.session_token
        self.dashboard = DashboardWindow(self.tcp_controller, username, token)
        self.dashboard.show()
        self.close()

    # --------------------------------------------------------------- close
    def closeEvent(self, event) -> None:
        if not self._completed:
            self.tcp_controller.stop()
        super().closeEvent(event)
