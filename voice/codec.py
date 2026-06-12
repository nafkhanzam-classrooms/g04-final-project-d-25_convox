"""Minimal audio codec - PCM format."""
from typing import Tuple

# Audio parameters
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 20
FRAME_SIZE = (SAMPLE_RATE * FRAME_DURATION_MS) // 1000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit audio


def encode_pcm(audio_data: bytes) -> bytes:
    """Pass-through encoding for PCM."""
    return audio_data


def decode_pcm(audio_data: bytes) -> bytes:
    """Pass-through decoding for PCM."""
    return audio_data


def get_audio_params() -> Tuple[int, int, int, int]:
    """Return (sample_rate, frame_size, channels, sample_width)."""
    return SAMPLE_RATE, FRAME_SIZE, CHANNELS, SAMPLE_WIDTH
