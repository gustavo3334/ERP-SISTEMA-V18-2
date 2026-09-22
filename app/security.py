from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config import settings


try:
    from pwdlib import PasswordHash

    _password_hash = PasswordHash.recommended()
except ImportError:
    _password_hash = None


def _fallback_hash(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(derived).decode()


def _fallback_verify(password: str, encoded: str) -> bool:
    try:
        _, salt_b64, hash_b64 = encoded.split("$", 2)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    if _password_hash is not None:
        return _password_hash.hash(password)
    return _fallback_hash(password)


def verify_password(password: str, encoded: str) -> bool:
    if encoded.startswith("scrypt$"):
        return _fallback_verify(password, encoded)
    if _password_hash is None:
        return False
    try:
        return _password_hash.verify(password, encoded)
    except Exception:
        return False


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_minutes
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expires,
        "iat": datetime.now(timezone.utc),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
