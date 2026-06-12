"""Notification system for desktop notifications."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QApplication

from utils.logger import get_logger


class NotificationWidget(QWidget):
    """Toast notification display."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger("NotificationWidget")
        self.notifications = []
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize UI."""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(QApplication.primaryScreen().availableGeometry().right() - 350, 10, 350, 0)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.setLayout(layout)

    def show_notification(self, title: str, message: str, duration: int = 5000) -> None:
        """Show notification toast."""
        notif_widget = QWidget()
        notif_widget.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 1px solid #0078d4;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        notif_widget.setMinimumWidth(330)
        notif_widget.setMaximumWidth(330)

        notif_layout = QVBoxLayout()
        notif_layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #ffffff;")
        notif_layout.addWidget(title_label)

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: #cccccc; font-size: 10px;")
        notif_layout.addWidget(message_label)

        notif_widget.setLayout(notif_layout)
        notif_widget.setMinimumHeight(80)

        self.layout().addWidget(notif_widget)
        self.notifications.append(notif_widget)

        # Auto-hide after duration
        QTimer.singleShot(duration, lambda: self.remove_notification(notif_widget))

    def remove_notification(self, widget: QWidget) -> None:
        """Remove notification from display."""
        if widget in self.notifications:
            self.notifications.remove(widget)
        self.layout().removeWidget(widget)
        widget.deleteLater()
