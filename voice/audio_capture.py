"""Audio capture from microphone."""
import threading
from typing import Callable, Optional

from voice.codec import SAMPLE_RATE, FRAME_SIZE, CHANNELS, SAMPLE_WIDTH
from utils.logger import get_logger


class AudioCapture:
    def __init__(self, on_frame: Callable[[bytes], None]) -> None:
        self.on_frame = on_frame
        self.logger = get_logger("AudioCapture")
        self.recording = False
        self.record_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start capturing audio from microphone."""
        try:
            import pyaudio

            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=FRAME_SIZE,
            )
            self.recording = True
            self.record_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.record_thread.start()
            self.logger.info("Audio capture started: %sHz, %d channels", SAMPLE_RATE, CHANNELS)
        except ImportError:
            self.logger.warning("PyAudio not available; audio capture disabled")
            self.recording = False

    def _capture_loop(self) -> None:
        while self.recording:
            try:
                data = self.stream.read(FRAME_SIZE, exception_on_overflow=False)
                self.on_frame(data)
            except Exception as exc:
                self.logger.exception("Error capturing audio: %s", exc)
                break

    def stop(self) -> None:
        """Stop capturing audio."""
        self.recording = False
        try:
            if hasattr(self, "stream"):
                self.stream.stop_stream()
                self.stream.close()
            if hasattr(self, "audio"):
                self.audio.terminate()
            self.logger.info("Audio capture stopped")
        except Exception as exc:
            self.logger.exception("Error stopping capture: %s", exc)
