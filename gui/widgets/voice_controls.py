"""Voice control widget."""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSpinBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from gui.controllers.tcp_controller import TCPController
from utils.logger import get_logger


class VoiceControls(QWidget):
    """Voice control panel with join/leave, mute, PTT controls."""

    voice_status_changed = pyqtSignal(str)  # "started", "stopped", "muted", "unmuted"

    def __init__(self, tcp_controller: TCPController):
        super().__init__()
        self.logger = get_logger("VoiceControls")
        self.tcp_controller = tcp_controller
        self.in_voice = False
        self.muted = False
        self.current_room = "global"

        self.init_ui()
        self.setMinimumHeight(50)
        self.setMaximumHeight(60)
        self.setStyleSheet("background-color: #1e1e1e; border-top: 1px solid #404040;")

    def init_ui(self) -> None:
        """Initialize UI components."""
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        # Status indicator
        self.status_label = QLabel("Voice: Offline")
        self.status_label.setStyleSheet("color: #808080; font-weight: bold;")
        layout.addWidget(self.status_label)

        layout.addSpacing(20)

        # Join/Leave button
        self.join_leave_btn = QPushButton("Join Voice")
        self.join_leave_btn.setMinimumHeight(35)
        self.join_leave_btn.setMaximumWidth(100)
        self.join_leave_btn.clicked.connect(self.toggle_voice)
        self.join_leave_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2fb34e;
            }
            QPushButton:pressed {
                background-color: #205c3a;
            }
        """)
        layout.addWidget(self.join_leave_btn)

        # Mute button
        self.mute_btn = QPushButton("Mute")
        self.mute_btn.setMinimumHeight(35)
        self.mute_btn.setMaximumWidth(80)
        self.mute_btn.setEnabled(False)
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.mute_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #505050;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover:!pressed {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #c41e3a;
            }
        """)
        layout.addWidget(self.mute_btn)

        # Speaking indicator
        self.speaking_label = QLabel("🔇 Idle")
        self.speaking_label.setStyleSheet("color: #808080; font-size: 11px;")
        layout.addWidget(self.speaking_label)

        # Volume indicator
        layout.addSpacing(20)
        volume_label = QLabel("Volume:")
        volume_label.setStyleSheet("color: #ffffff; font-size: 11px;")
        layout.addWidget(volume_label)

        self.volume_slider = QSpinBox()
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setMaximumWidth(60)
        self.volume_slider.setStyleSheet("""
            QSpinBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.volume_slider)

        # Participant count
        layout.addSpacing(20)
        self.participants_label = QLabel("Participants: 0")
        self.participants_label.setStyleSheet("color: #ffffff; font-size: 11px;")
        layout.addWidget(self.participants_label)

        layout.addStretch()

        self.setLayout(layout)

    def toggle_voice(self) -> None:
        """Toggle voice connection."""
        if not self.in_voice:
            self.start_voice()
        else:
            self.stop_voice()

    def start_voice(self) -> None:
        """Start voice communication."""
        # Use a default UDP port (would be dynamic in production)
        udp_port = 9001
        self.tcp_controller.send_voice_start(self.current_room, udp_port)
        self.in_voice = True
        self.update_ui_state()
        self.logger.info("Voice started in %s", self.current_room)

    def stop_voice(self) -> None:
        """Stop voice communication."""
        self.tcp_controller.send_voice_stop(self.current_room)
        self.in_voice = False
        self.muted = False
        self.update_ui_state()
        self.logger.info("Voice stopped")

    def toggle_mute(self) -> None:
        """Toggle mute state."""
        if not self.in_voice:
            return

        self.muted = not self.muted
        status = "muted" if self.muted else "unmuted"
        self.tcp_controller.send_voice_status(self.current_room, status)
        self.update_ui_state()
        self.logger.info("Mute toggled: %s", status)

    def set_room(self, room: str) -> None:
        """Set current room."""
        self.current_room = room
        # If in voice, would need to switch voice room
        if self.in_voice:
            self.stop_voice()

    def update_participants_count(self, count: int) -> None:
        """Update participant count display."""
        self.participants_label.setText(f"Participants: {count}")

    def update_ui_state(self) -> None:
        """Update button states based on voice state."""
        if self.in_voice:
            self.status_label.setText("Voice: Online")
            self.status_label.setStyleSheet("color: #00d944; font-weight: bold;")
            self.join_leave_btn.setText("Leave Voice")
            self.join_leave_btn.setStyleSheet("""
                QPushButton {
                    background-color: #c41e3a;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            self.mute_btn.setEnabled(True)

            if self.muted:
                self.mute_btn.setText("Unmute")
                self.mute_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #c41e3a;
                        color: #ffffff;
                        border: none;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #d32f2f;
                    }
                """)
                self.speaking_label.setText("🔇 Muted")
                self.speaking_label.setStyleSheet("color: #c41e3a; font-size: 11px; font-weight: bold;")
            else:
                self.mute_btn.setText("Mute")
                self.mute_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #404040;
                        color: #ffffff;
                        border: 1px solid #505050;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #505050;
                    }
                """)
                self.speaking_label.setText("🔊 Live")
                self.speaking_label.setStyleSheet("color: #00d944; font-size: 11px; font-weight: bold;")
        else:
            self.status_label.setText("Voice: Offline")
            self.status_label.setStyleSheet("color: #808080; font-weight: bold;")
            self.join_leave_btn.setText("Join Voice")
            self.join_leave_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #2fb34e;
                }
            """)
            self.mute_btn.setEnabled(False)
            self.mute_btn.setText("Mute")
            self.speaking_label.setText("🔇 Offline")
            self.speaking_label.setStyleSheet("color: #808080; font-size: 11px;")
