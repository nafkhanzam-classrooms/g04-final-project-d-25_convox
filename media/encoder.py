import base64


def encode_bytes(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def decode_bytes(encoded: str) -> bytes:
    return base64.b64decode(encoded.encode("ascii"))
