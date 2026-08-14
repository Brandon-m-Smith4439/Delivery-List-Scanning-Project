# File: tests/test_auth_passwords.py
"""Regression coverage for portable password hashing and authentication."""

from __future__ import annotations

import hashlib
import _hashlib
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from backend.config import load_config
from backend.store import (
    PASSWORD_ITERATIONS,
    SQLiteDeliveryStore,
    _pbkdf2_hmac_sha256,
    hash_password,
    verify_password,
)


ROOT = Path(__file__).resolve().parents[1]


class PasswordCompatibilityTests(unittest.TestCase):
    def test_portable_pbkdf2_matches_standard_library(self) -> None:
        password = b"FloorScannerPassword!"
        salt = b"0123456789abcdef"
        expected = hashlib.pbkdf2_hmac("sha256", password, salt, 128)

        with mock.patch.object(hashlib, "pbkdf2_hmac", None):
            actual = _pbkdf2_hmac_sha256(password, salt, 128)

        self.assertEqual(actual, expected)

    def test_pure_python_pbkdf2_matches_standard_library(self) -> None:
        password = b"FloorScannerPassword!"
        salt = b"fedcba9876543210"
        expected = hashlib.pbkdf2_hmac("sha256", password, salt, 128)

        with (
            mock.patch.object(hashlib, "pbkdf2_hmac", None),
            mock.patch.object(_hashlib, "pbkdf2_hmac", None),
        ):
            actual = _pbkdf2_hmac_sha256(password, salt, 128)

        self.assertEqual(actual, expected)

    def test_existing_hash_format_verifies_without_hashlib_attribute(self) -> None:
        stored_hash = hash_password("CorrectHorseBatteryStaple!")

        with mock.patch.object(hashlib, "pbkdf2_hmac", None):
            self.assertTrue(verify_password("CorrectHorseBatteryStaple!", stored_hash))
            self.assertFalse(verify_password("wrong-password", stored_hash))

    def test_password_reset_then_login_works_without_hashlib_attribute(self) -> None:
        folder = ROOT / "_verification" / "auth-passwords"
        folder.mkdir(parents=True, exist_ok=True)
        database_path = folder / "scanner.db"
        for suffix in ("", "-shm", "-wal"):
            candidate = Path(f"{database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        try:
            config = replace(
                load_config(ROOT),
                root=folder,
                data_dir=folder,
                database_path=database_path,
                temp_delivery_lists_dir=folder,
                sample_path=ROOT / "data" / "sample-delivery-list.json",
                environment="development",
                default_admin_username="admin",
                default_admin_password="OriginalPassword!",
            )
            store = SQLiteDeliveryStore(config)
            store.initialize()

            with mock.patch.object(hashlib, "pbkdf2_hmac", None):
                reset = store.request_password_reset("admin")
                store.confirm_password_reset("admin", reset["resetCode"], "ReplacementPassword!")
                authenticated = store.authenticate_user("admin", "ReplacementPassword!")

            self.assertEqual(authenticated["user"]["username"], "admin")
            self.assertGreater(PASSWORD_ITERATIONS, 0)
        finally:
            for suffix in ("", "-shm", "-wal"):
                candidate = Path(f"{database_path}{suffix}")
                if candidate.exists():
                    candidate.unlink()


if __name__ == "__main__":
    unittest.main()
