"""Upload/download widget for file transfer."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QProgressBar, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from gui.controllers.tcp_controller import TCPController
from utils.logger import get_logger


class UploadWidget(QWidget):
    """File upload widget with drag-drop support."""

    file_selected = pyqtSignal(str)  # file_path

    def __init__(self, tcp_controller: TCPController):
        super().__init__()
        self.logger = get_logger("UploadWidget")
        self.tcp_controller = tcp_controller
        self.current_transfer_id: str = None
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("File Transfer")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        layout.addWidget(title)

        # Upload button
        self.upload_btn = QPushButton("📁 Choose File")
        self.upload_btn.setMinimumHeight(35)
        self.upload_btn.clicked.connect(self.choose_file)
        self.upload_btn.setStyleSheet("""
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
        layout.addWidget(self.upload_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e1e1e;
                border: 1px solid #404040;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)
        self.setMaximumHeight(150)

    def choose_file(self) -> None:
        """Open file chooser dialog."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose File")
        if file_path:
            self.file_selected.emit(file_path)
            self.status_label.setText(f"Selected: {file_path.split('/')[-1]}")
            self.logger.info("File selected: %s", file_path)

    def start_upload(self, transfer_id: str, filename: str) -> None:
        """Start file upload progress."""
        self.current_transfer_id = transfer_id
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Uploading: {filename}")

    def update_progress(self, progress: int) -> None:
        """Update upload progress."""
        self.progress_bar.setValue(progress)

    def complete_upload(self) -> None:
        """Mark upload as complete."""
        self.progress_bar.setValue(100)
        self.status_label.setText("Upload complete!")

    def error_upload(self, error_msg: str) -> None:
        """Handle upload error."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error_msg}")
        self.status_label.setStyleSheet("color: #c41e3a;")
