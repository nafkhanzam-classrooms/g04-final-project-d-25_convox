import base64
import os
from pathlib import Path
from typing import Tuple

from storage.storage_manager import StorageManager
from utils.logger import get_logger

ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024

logger = get_logger("ImageTransfer")
storage = StorageManager()


def image_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def validate_image(filename: str, data: bytes) -> Tuple[bool, str]:
    ext = image_extension(filename)
    if ext not in ALLOWED_IMAGE_TYPES:
        return False, f"Unsupported image format: {ext}."
    if len(data) == 0:
        return False, "Image data is empty."
    if len(data) > MAX_IMAGE_SIZE:
        return False, f"Image exceeds maximum size of {MAX_IMAGE_SIZE} bytes."
    return True, ""


def save_image(sender: str, room: str, filename: str, image_data: bytes) -> Path:
    target = storage.room_upload_path(room, filename)
    storage.save_file(target, image_data)
    logger.info("Saved image %s from %s to %s", filename, sender, target)
    return target


def encode_image(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def decode_image(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))
