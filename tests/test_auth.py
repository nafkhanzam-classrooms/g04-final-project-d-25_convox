"""Unit tests for the lightweight authentication module."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db import Database  # noqa: E402
from server.auth import (  # noqa: E402
    AuthService,
    hash_password,
    validate_password,
    validate_username,
    verify_password,
)


class HashTests(unittest.TestCase):
    def test_hash_round_trip(self) -> None:
        encoded = hash_password("hunter2")
        self.assertNotIn("hunter2", encoded)
        self.assertTrue(verify_password("hunter2", encoded))
        self.assertFalse(verify_password("hunter3", encoded))

    def test_verify_rejects_invalid_format(self) -> None:
        self.assertFalse(verify_password("hunter2", ""))
        self.assertFalse(verify_password("hunter2", "not-a-real-hash"))

    def test_distinct_salts(self) -> None:
        a = hash_password("hunter2")
        b = hash_password("hunter2")
        self.assertNotEqual(a, b)


class ValidationTests(unittest.TestCase):
    def test_username_rules(self) -> None:
        self.assertEqual(validate_username("fab.ian"), "fab.ian")
        self.assertEqual(validate_username("  alice  "), "alice")
        with self.assertRaises(ValueError):
            validate_username("ab")
        with self.assertRaises(ValueError):
            validate_username("alice space")
        with self.assertRaises(ValueError):
            validate_username("alice@example.com")

    def test_password_rules(self) -> None:
        validate_password("123456")
        with self.assertRaises(ValueError):
            validate_password("short")
        with self.assertRaises(ValueError):
            validate_password(" leadingspace")


class AuthServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db = Database(db_path=self._tmp.name)
        self.auth = AuthService(self.db)

    def tearDown(self) -> None:
        try:
            self.db.connection.close()
        finally:
            os.unlink(self._tmp.name)

    def test_register_then_authenticate(self) -> None:
        self.auth.register("fabian", "hunter22")
        self.assertEqual(self.auth.authenticate("fabian", "hunter22"), "fabian")

    def test_register_duplicate_rejected(self) -> None:
        self.auth.register("fabian", "hunter22")
        with self.assertRaises(ValueError):
            self.auth.register("fabian", "another1")

    def test_login_unknown_user_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.auth.authenticate("ghost", "hunter22")

    def test_wrong_password_rejected(self) -> None:
        self.auth.register("fabian", "hunter22")
        with self.assertRaises(ValueError):
            self.auth.authenticate("fabian", "nope1234")


if __name__ == "__main__":
    unittest.main()
