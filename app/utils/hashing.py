import hashlib
import secrets


def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
