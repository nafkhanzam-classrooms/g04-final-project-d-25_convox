"""Toast-style desktop notifications floating on top of the dashboard."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from gui.styles import colors
from utils.logger import get_logger


class NotificationWidget(QWidget):
    """Stack of auto-expiring toast notifications."""

    DEFAULT_DURATION_MS = 4500

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.logger = get_logger("NotificationWidget")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(340)
        self._reposition()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._layout = layout

    def _reposition(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        rect = screen.availableGeometry()
        self.move(rect.right() - self.width() - 24, rect.top() + 24)

    # ----------------------------------------------------------------- public
    def show_notification(
        self,
        title: str,
        message: str,
        duration_ms: int | None = None,
    ) -> None:
        toast = self._build_toast(title, message)
        self._layout.addWidget(toast)
        self.adjustSize()
        if not self.isVisible():
            self.show()
        QTimer.singleShot(duration_ms or self.DEFAULT_DURATION_MS, lambda: self._dismiss(toast))

    # ------------------------------------------------------------- internals
    def _build_toast(self, title: str, message: str) -> QWidget:
        toast = QWidget()
        toast.setObjectName("toast")
        toast.setStyleSheet(
            f"""
            #toast {{
                background-color: {colors.BG_RAISED};
                border: 1px solid {colors.BORDER_STRONG};
                border-left: 3px solid {colors.ACCENT};
                border-radius: 8px;
            }}
            QLabel {{ background: transparent; }}
            """
        )
        layout = QVBoxLayout(toast)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; font-weight: 700;")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        body = QLabel(message)
        body.setWordWrap(True)
        body.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(body)
        return toast

    def _dismiss(self, toast: QWidget) -> None:
        try:
            self._layout.removeWidget(toast)
            toast.deleteLater()
            self.adjustSize()
            if self._layout.count() == 0:
                self.hide()
        except Exception as exc:  # noqa: BLE001
            self.logger.exception("Failed to dismiss toast: %s", exc)
