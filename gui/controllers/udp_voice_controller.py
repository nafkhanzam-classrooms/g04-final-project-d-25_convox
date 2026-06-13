"""GUI-side UDP voice controller.

Wraps the existing ``voice.UDPVoiceClient`` plus mic capture / playback
in a Qt-friendly facade that the GUI can drive without touching sockets
directly. Falls back gracefully when PyAudio is not installed - the GUI
will still join the room (so other clients see participation) but no
audio is sent or played back.
"""

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from gui.controllers.event_dispatcher import get_dispatcher
from utils.logger import get_logger


class UDPVoiceController(QObject):
    """Thin orchestration layer above voice/* primitives."""

    voice_state_changed = pyqtSignal(bool)        # connected
    mute_state_changed = pyqtSignal(bool)         # muted
    audio_unavailable = pyqtSignal(str)           # reason

    def __init__(
        self,
        username: str,
        server_host: str = "127.0.0.1",
        server_port: int = 9001,
    ) -> None:
        super().__init__()
        self.username = username
        self.server_host = server_host
        self.server_port = server_port
        self.dispatcher = get_dispatcher()
        self.logger = get_logger("UDPVoiceController")

        self._client = None
        self._capture = None
        self._playback = None
        self._connected = False
        self._muted = False
        self._current_room: Optional[str] = None

    # ----------------------------------------------------------------- queries
    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def local_port(self) -> int:
        return getattr(self._client, "local_port", 0) or 0

    # --------------------------------------------------------------- lifecycle
    def join(self, room: str) -> Optional[int]:
        """Open the UDP socket + audio devices and join ``room``.

        Returns the local UDP port the client is bound to, or ``None`` if
        the voice subsystem could not be initialised.
        """
        if self._connected:
            return self.local_port

        try:
            from voice.udp_client import UDPVoiceClient
            from voice.audio_capture import AudioCapture
            from voice.audio_playback import AudioPlayback
        except ImportError as exc:
            self.logger.warning("Voice modules unavailable: %s", exc)
            self.audio_unavailable.emit(str(exc))
            return None

        try:
            playback = AudioPlayback()
            playback.start()

            client = UDPVoiceClient(
                username=self.username,
                server_host=self.server_host,
                server_port=self.server_port,
            )
            client.start()

            def _on_frame(packet) -> None:
                playback.queue_frame(packet.audio_data)

            client.on_frame_received = _on_frame  # type: ignore[assignment]
            client.join_room(room)

            capture = AudioCapture(on_frame=self._on_capture_frame)
            capture.start()

            self._client = client
            self._capture = capture
            self._playback = playback
            self._current_room = room
            self._connected = True
            self._muted = False
            self.voice_state_changed.emit(True)
            self.mute_state_changed.emit(False)
            self.logger.info("Joined voice room %s on port %s", room, client.local_port)
            return client.local_port
        except Exception as exc:  # noqa: BLE001 - audio stack can raise many errors
            self.logger.exception("Voice setup failed: %s", exc)
            self.audio_unavailable.emit(str(exc))
            self.leave()
            return None

    def leave(self) -> None:
        try:
            if self._capture is not None:
                self._capture.stop()
            if self._client is not None:
                self._client.leave_room()
                self._client.stop()
            if self._playback is not None:
                self._playback.stop()
        except Exception as exc:  # noqa: BLE001
            self.logger.exception("Error tearing down voice: %s", exc)
        finally:
            self._client = None
            self._capture = None
            self._playback = None
            self._connected = False
            self._muted = False
            self._current_room = None
            self.voice_state_changed.emit(False)
            self.mute_state_changed.emit(False)

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        self.mute_state_changed.emit(self._muted)

    def toggle_mute(self) -> bool:
        self.set_muted(not self._muted)
        return self._muted

    # --------------------------------------------------------------- internals
    def _on_capture_frame(self, frame: bytes) -> None:
        if self._muted or not self._connected or self._client is None:
            return
        self._client.send_frame(frame)
