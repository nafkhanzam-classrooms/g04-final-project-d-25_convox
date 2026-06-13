"""Voice control bar (join, mute, status indicator)."""

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpacerItem,
    QSizePolicy,
    QWidget,
)
from PyQt6.QtCore import Qt

from gui.controllers.event_dispatcher import get_dispatcher
from gui.controllers.tcp_controller import TCPController
from gui.controllers.udp_voice_controller import UDPVoiceController
from gui.styles import colors
from utils.logger import get_logger


class VoiceControls(QWidget):
    """Bottom voice control bar. Join/leave, mute/unmute, status."""

    voice_status_changed = pyqtSignal(str)  # "started" | "stopped" | "muted" | "unmuted"

    def __init__(
        self,
        tcp_controller: TCPController,
        voice_controller: Optional[UDPVoiceController] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.logger = get_logger("VoiceControls")
        self.tcp_controller = tcp_controller
        self.voice_controller = voice_controller
        self.dispatcher = get_dispatcher()
        self.in_voice = False
        self.muted = False
        self.current_room = "global"
        self.setFixedHeight(56)
        self.setObjectName("voiceBar")
        self.setStyleSheet(
            f"#voiceBar {{ background-color: {colors.BG_DEEPEST}; "
            f"border-top: 1px solid {colors.BORDER_SOFT}; }}"
        )
        self._build()
        if self.voice_controller is not None:
            self.voice_controller.voice_state_changed.connect(self._on_voice_state)
            self.voice_controller.mute_state_changed.connect(self._on_mute_state)
            self.voice_controller.audio_unavailable.connect(self._on_audio_unavailable)

    # ---------------------------------------------------------------- layout
    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        self.status_label = QLabel("Voice Offline")
        self.status_label.setStyleSheet(
            f"color: {colors.TEXT_MUTED}; font-weight: 600;"
        )
        layout.addWidget(self.status_label)

        layout.addItem(QSpacerItem(10, 1, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        self.join_leave_btn = QPushButton("Join Voice")
        self.join_leave_btn.setProperty("variant", "success")
        self.join_leave_btn.setMinimumWidth(110)
        self.join_leave_btn.clicked.connect(self.toggle_voice)
        layout.addWidget(self.join_leave_btn)

        self.mute_btn = QPushButton("Mute")
        self.mute_btn.setProperty("variant", "subtle")
        self.mute_btn.setEnabled(False)
        self.mute_btn.setMinimumWidth(90)
        self.mute_btn.clicked.connect(self.toggle_mute)
        layout.addWidget(self.mute_btn)

        self.ptt_btn = QPushButton("Push-to-Talk")
        self.ptt_btn.setCheckable(True)
        self.ptt_btn.setProperty("variant", "ghost")
        self.ptt_btn.toggled.connect(self._on_ptt_toggled)
        layout.addWidget(self.ptt_btn)

        layout.addStretch(1)

        layout.addWidget(QLabel("Volume"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(110)
        layout.addWidget(self.volume_slider)

        self.participants_label = QLabel("Participants: 0")
        self.participants_label.setProperty("role", "muted")
        self.participants_label.setStyleSheet(f"color: {colors.TEXT_MUTED};")
        layout.addWidget(self.participants_label)

    # ----------------------------------------------------------------- state
    def set_room(self, room: str) -> None:
        if self.in_voice and room != self.current_room:
            self.stop_voice()
        self.current_room = room

    def update_participants_count(self, count: int) -> None:
        self.participants_label.setText(f"Participants: {count}")

    # -------------------------------------------------------------- handlers
    def toggle_voice(self) -> None:
        if not self.in_voice:
            self.start_voice()
        else:
            self.stop_voice()

    def start_voice(self) -> None:
        udp_port = 0
        if self.voice_controller is not None:
            udp_port = self.voice_controller.join(self.current_room) or 0
        # Even without local audio we still tell the server we are joining
        # so other participants see us in the voice room.
        self.tcp_controller.send_voice_start(self.current_room, udp_port)
        self.in_voice = True
        self.muted = False if self.voice_controller is None else self.voice_controller.muted
        self._render()
        self.voice_status_changed.emit("started")
        self.logger.info("Voice started in %s (port=%s)", self.current_room, udp_port)

    def stop_voice(self) -> None:
        if self.voice_controller is not None:
            self.voice_controller.leave()
        self.tcp_controller.send_voice_stop(self.current_room)
        self.in_voice = False
        self.muted = False
        self._render()
        self.voice_status_changed.emit("stopped")
        self.logger.info("Voice stopped")

    def toggle_mute(self) -> None:
        if not self.in_voice:
            return
        if self.voice_controller is not None:
            self.muted = self.voice_controller.toggle_mute()
        else:
            self.muted = not self.muted
        status = "muted" if self.muted else "unmuted"
        self.tcp_controller.send_voice_status(self.current_room, status)
        self._render()
        self.voice_status_changed.emit(status)

    def _on_ptt_toggled(self, checked: bool) -> None:
        if not self.in_voice or self.voice_controller is None:
            return
        # Push-to-talk: while the toggle is on we send audio, otherwise
        # we hold mute on the controller. The button label tells the user
        # what state they're in.
        self.voice_controller.set_muted(not checked)
        self.muted = not checked
        status = "muted" if self.muted else "unmuted"
        self.tcp_controller.send_voice_status(self.current_room, status)
        self._render()

    # ---------------------------------------------------------------- render
    def _render(self) -> None:
        if self.in_voice:
            self.status_label.setText(f"Voice • {self.current_room}")
            self.status_label.setStyleSheet(
                f"color: {colors.SUCCESS}; font-weight: 700;"
            )
            self.join_leave_btn.setText("Leave Voice")
            self.join_leave_btn.setProperty("variant", "danger")
            self.mute_btn.setEnabled(True)
            self.mute_btn.setText("Unmute" if self.muted else "Mute")
            self.mute_btn.setProperty("variant", "danger" if self.muted else "subtle")
            self.ptt_btn.setEnabled(True)
        else:
            self.status_label.setText("Voice Offline")
            self.status_label.setStyleSheet(
                f"color: {colors.TEXT_MUTED}; font-weight: 600;"
            )
            self.join_leave_btn.setText("Join Voice")
            self.join_leave_btn.setProperty("variant", "success")
            self.mute_btn.setEnabled(False)
            self.mute_btn.setText("Mute")
            self.mute_btn.setProperty("variant", "subtle")
            self.ptt_btn.setEnabled(False)
            self.ptt_btn.setChecked(False)
        self._restyle()

    def _restyle(self) -> None:
        # Force re-evaluation of dynamic ``variant`` property.
        for btn in (self.join_leave_btn, self.mute_btn, self.ptt_btn):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # -------------------------------------------------------------- callbacks
    def _on_voice_state(self, connected: bool) -> None:
        if connected != self.in_voice:
            self.in_voice = connected
            self._render()

    def _on_mute_state(self, muted: bool) -> None:
        self.muted = muted
        self._render()

    def _on_audio_unavailable(self, reason: str) -> None:
        self.logger.warning("Audio unavailable: %s", reason)
        QMessageBox.warning(
            self,
            "Voice Unavailable",
            "Audio devices could not be initialised. You will appear in the "
            "voice room but no audio will be sent or received.\n\n"
            f"Details: {reason}",
        )
