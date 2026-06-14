"""Lightweight password-based authentication.

Scope: simple, networking-project grade. We keep the implementation tiny
and dependency-free (``hashlib`` only) so the auth path remains easy to
demo and reason about.

Design:
* Passwords are hashed with PBKDF2-HMAC-SHA256 (100k iterations) using a
  per-user 16-byte random salt.
* The stored format is ``"pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>"``
  so we can rotate iteration counts without breaking older rows.
* ``verify_password`` performs a constant-time comparison.
"""

from __future__ import annotations

import hmac
import os
import re
import secrets
from hashlib import pbkdf2_hmac

from database.db import Database


_ALGO = "pbkdf2_sha256"
_ITERATIONS = 100_000
_SALT_BYTES = 16
_HASH_BYTES = 32

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_\-\.]{3,32}$")
MIN_PASSWORD_LEN = 6
MAX_PASSWORD_LEN = 128


# ---------------------------------------------------------------------- hashing
def hash_password(password: str) -> str:
    """Return an encoded PBKDF2 hash for ``password``."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    salt = os.urandom(_SALT_BYTES)
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS, _HASH_BYTES)
    return f"{_ALGO}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time comparison of ``password`` against ``encoded``."""
    if not encoded or not isinstance(password, str):
        return False
    try:
        algo, iterations_str, salt_hex, hash_hex = encoded.split("$")
    except ValueError:
        return False
    if algo != _ALGO:
        return False
    try:
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    candidate = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, len(expected))
    return hmac.compare_digest(candidate, expected)


# ----------------------------------------------------------------------- input
def validate_username(username: str) -> str:
    """Return a normalised username or raise ``ValueError``."""
    if not isinstance(username, str):
        raise ValueError("Username must be a string.")
    candidate = username.strip()
    if not _USERNAME_RE.match(candidate):
        raise ValueError(
            "Username must be 3-32 characters and contain only letters, "
            "digits, '_', '-' or '.'"
        )
    return candidate


def validate_password(password: str) -> str:
    if not isinstance(password, str):
        raise ValueError("Password must be a string.")
    if not (MIN_PASSWORD_LEN <= len(password) <= MAX_PASSWORD_LEN):
        raise ValueError(
            f"Password must be between {MIN_PASSWORD_LEN} and "
            f"{MAX_PASSWORD_LEN} characters."
        )
    if password.strip() != password:
        raise ValueError("Password must not start or end with whitespace.")
    return password


# --------------------------------------------------------------------- service
class AuthService:
    """Auth helper that stores credentials in the existing SQLite DB."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def register(self, username: str, password: str) -> str:
        """Create a new account. Raises ``ValueError`` on conflict / invalid."""
        username = validate_username(username)
        validate_password(password)
        existing_hash = self.database.get_user_password_hash(username)
        if existing_hash:
            raise ValueError("Username already registered.")
        self.database.set_user_password(username, hash_password(password))
        return username

    def authenticate(self, username: str, password: str) -> str:
        """Return the canonical username on success, raise on failure."""
        username = validate_username(username)
        if not isinstance(password, str) or not password:
            raise ValueError("Password is required.")
        stored = self.database.get_user_password_hash(username)
        if not stored:
            raise ValueError("Invalid username or password.")
        if not verify_password(password, stored):
            raise ValueError("Invalid username or password.")
        return username

    def has_account(self, username: str) -> bool:
        return bool(self.database.get_user_password_hash(username))
