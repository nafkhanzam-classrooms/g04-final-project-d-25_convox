"""Upload helper widget shown next to the message input."""

import os
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.controllers.event_dispatcher import get_dispatcher
from gui.controllers.tcp_controller import TCPController
from gui.styles import colors
from utils.logger import get_logger


class UploadWidget(QWidget):
    """File chooser + progress display sitting next to the chat input."""

    file_selected = pyqtSignal(str)  # absolute path of the file the user picked

    def __init__(
        self,
        tcp_controller: TCPController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.logger = get_logger("UploadWidget")
        self.tcp_controller = tcp_controller
        self.dispatcher = get_dispatcher()
        self._current_transfer_id: Optional[str] = None
        self._build()
        self._wire_signals()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        button_row = QHBoxLayout()
        button_row.setSpacing(6)

        self.upload_btn = QPushButton("📎")
        self.upload_btn.setToolTip("Send file or image")
        self.upload_btn.setProperty("variant", "subtle")
        self.upload_btn.setFixedWidth(40)
        self.upload_btn.clicked.connect(self.choose_file)
        button_row.addWidget(self.upload_btn)
        layout.addLayout(button_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {colors.TEXT_MUTED}; font-size: 11px;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

    def _wire_signals(self) -> None:
        self.dispatcher.file_transfer_started.connect(self._on_started)
        self.dispatcher.file_transfer_progress.connect(self._on_progress)
        self.dispatcher.file_transfer_complete.connect(self._on_complete)
        self.dispatcher.file_transfer_error.connect(self._on_error)

    # ----------------------------------------------------------------- public
    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose File")
        if not path:
            return
        self.file_selected.emit(path)
        filename = os.path.basename(path)
        self.status_label.setText(f"Selected {filename}")
        self.status_label.setVisible(True)
        self.logger.info("File selected: %s", path)

    # -------------------------------------------------------------- handlers
    def _on_started(self, transfer_id: str, filename: str, _filesize: int) -> None:
        self._current_transfer_id = transfer_id
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Uploading {filename}…")
        self.status_label.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 11px;")
        self.status_label.setVisible(True)

    def _on_progress(self, transfer_id: str, progress: int) -> None:
        if transfer_id != self._current_transfer_id:
            return
        self.progress_bar.setValue(max(0, min(100, progress)))

    def _on_complete(self, transfer_id: str) -> None:
        if transfer_id != self._current_transfer_id:
            return
        self.progress_bar.setValue(100)
        self.status_label.setText("Upload complete")
        self.status_label.setStyleSheet(f"color: {colors.SUCCESS}; font-size: 11px;")

    def _on_error(self, transfer_id: str, error: str) -> None:
        if transfer_id != self._current_transfer_id:
            return
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet(f"color: {colors.DANGER}; font-size: 11px;")
