"""Login window for Convox GUI."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QProgressBar, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon

from gui.controllers.tcp_controller import TCPController
from gui.controllers.event_dispatcher import get_dispatcher
from gui.windows.dashboard_window import DashboardWindow
from utils.logger import get_logger


class LoginWindow(QMainWindow):
    """Login window for user authentication."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger("LoginWindow")
        self.tcp_controller = TCPController()
        self.dispatcher = get_dispatcher()
        self.dashboard: DashboardWindow = None
        self.session_token: str = None

        self.init_ui()
        self.connect_signals()
        self.setWindowTitle("Convox - Login")
        self.setGeometry(100, 100, 500, 300)

    def init_ui(self) -> None:
        """Initialize UI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title = QLabel("CONVOX")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Realtime Communication Platform")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Username input
        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.returnPressed.connect(self.attempt_login)
        layout.addWidget(self.username_input)

        # Session token for reconnect
        layout.addWidget(QLabel("Session Token (optional):"))
        self.session_input = QLineEdit()
        self.session_input.setPlaceholderText("Leave blank for new login, or paste token to reconnect")
        self.session_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.session_input)

        layout.addSpacing(10)

        # Remember me checkbox
        self.remember_checkbox = QCheckBox("Remember session token")
        layout.addWidget(self.remember_checkbox)

        layout.addSpacing(20)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addSpacing(20)

        # Login button
        button_layout = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.login_button.setMinimumHeight(40)
        self.login_button.clicked.connect(self.attempt_login)
        button_layout.addWidget(self.login_button)
        layout.addLayout(button_layout)

        layout.addStretch()
        central_widget.setLayout(layout)

        # Apply styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1084d7;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QCheckBox {
                color: #ffffff;
            }
        """)

    def connect_signals(self) -> None:
        """Connect event signals."""
        self.dispatcher.login_success.connect(self.on_login_success)
        self.dispatcher.login_failed.connect(self.on_login_failed)
        self.dispatcher.session_restored.connect(self.on_session_restored)
        self.dispatcher.connection_error.connect(self.on_connection_error)
        self.dispatcher.error.connect(self.on_error)

    def attempt_login(self) -> None:
        """Attempt to login or reconnect."""
        username = self.username_input.text().strip()
        session_token = self.session_input.text().strip()

        if not username:
            QMessageBox.warning(self, "Validation Error", "Please enter a username")
            return

        self.login_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Connecting to server...")

        self.tcp_controller.start()

        if session_token:
            self.session_token = session_token
            self.tcp_controller.reconnect(session_token)
        else:
            self.tcp_controller.login(username)

    def on_login_success(self, username: str) -> None:
        """Handle successful login."""
        self.logger.info("Login successful for %s", username)
        self.status_label.setText(f"Welcome, {username}!")

        QTimer.singleShot(1000, self.open_dashboard)

    def on_session_restored(self, username: str, room: str) -> None:
        """Handle successful session restoration."""
        self.logger.info("Session restored for %s in room %s", username, room)
        self.status_label.setText(f"Session restored! Welcome back, {username}!")

        QTimer.singleShot(1000, self.open_dashboard)

    def on_login_failed(self, error_message: str) -> None:
        """Handle login failure."""
        self.logger.warning("Login failed: %s", error_message)
        self.progress_bar.setVisible(False)
        self.login_button.setEnabled(True)
        QMessageBox.critical(self, "Login Failed", error_message)

    def on_connection_error(self, error_message: str) -> None:
        """Handle connection error."""
        self.logger.error("Connection error: %s", error_message)
        self.progress_bar.setVisible(False)
        self.login_button.setEnabled(True)
        QMessageBox.critical(self, "Connection Error", error_message)

    def on_error(self, error_message: str) -> None:
        """Handle general errors."""
        self.logger.error("Error: %s", error_message)
        self.progress_bar.setVisible(False)
        self.login_button.setEnabled(True)
        QMessageBox.critical(self, "Error", error_message)

    def open_dashboard(self) -> None:
        """Open dashboard window."""
        username = self.username_input.text().strip()
        self.dashboard = DashboardWindow(self.tcp_controller, username, self.session_token)
        self.dashboard.show()
        self.close()

    def closeEvent(self, event) -> None:
        """Clean up on window close."""
        self.tcp_controller.stop()
        super().closeEvent(event)
