from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import UserRole


def test_hash_password_and_verify():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_create_access_token():
    user_id = 42
    role = UserRole.AGENT
    token = create_access_token(subject=user_id, role=role)

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["role"] == role
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_access_token_custom_expiry():
    user_id = 1
    role = UserRole.CUSTOMER
    custom_delta = timedelta(minutes=5)
    token = create_access_token(
        subject=user_id, role=role, expires_delta=custom_delta
    )

    payload = decode_token(token)
    assert payload is not None
    now = datetime.now(UTC).timestamp()
    # Expire should be roughly 5 minutes (300s) from now
    assert payload["exp"] - now <= 305


def test_create_refresh_token():
    user_id = 99
    token = create_refresh_token(subject=user_id)

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert "role" not in payload
    assert "exp" in payload


def test_decode_token_invalid():
    assert decode_token("invalid.token.here") is None
    assert decode_token("") is None


def test_decode_token_expired():
    # Create an already expired token
    expired_time = datetime.now(UTC) - timedelta(minutes=10)
    to_encode = {
        "sub": "1",
        "exp": expired_time,
        "type": "access",
        "role": UserRole.CUSTOMER,
    }
    expired_token = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    assert decode_token(expired_token) is None


def test_decode_token_wrong_secret():
    to_encode = {
        "sub": "1",
        "exp": datetime.now(UTC) + timedelta(minutes=10),
        "type": "access",
        "role": UserRole.CUSTOMER,
    }
    wrong_secret_token = jwt.encode(
        to_encode,
        "wrong-secret-key-xyz-that-is-at-least-32-chars-long!",
        algorithm=settings.ALGORITHM,
    )

    assert decode_token(wrong_secret_token) is None


def test_utils_hashing():
    from app.utils.hashing import generate_token, sha256

    token = generate_token(16)
    assert len(token) > 0
    assert isinstance(token, str)

    hash_val = sha256("test")
    assert isinstance(hash_val, str)
    assert len(hash_val) == 64

