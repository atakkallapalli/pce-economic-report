import pytest  # noqa: F401

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_password_returns_hash(self):
        hashed = hash_password("TestPass123")
        assert hashed != "TestPass123"
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        hashed = hash_password("TestPass123")
        assert verify_password("TestPass123", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("TestPass123")
        assert verify_password("WrongPass123", hashed) is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("TestPass123")
        h2 = hash_password("TestPass123")
        assert h1 != h2


class TestJWT:
    def test_create_access_token(self):
        token = create_access_token({"sub": "user123", "role": "MEMBER"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        token = create_refresh_token({"sub": "user123"})
        assert isinstance(token, str)

    def test_decode_access_token(self):
        token = create_access_token({"sub": "user123", "role": "MEMBER"})
        payload = decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "MEMBER"
        assert payload["type"] == "access"

    def test_decode_refresh_token(self):
        token = create_refresh_token({"sub": "user123"})
        payload = decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        payload = decode_token("invalid_token")
        assert payload == {}

    def test_decode_empty_token(self):
        payload = decode_token("")
        assert payload == {}
