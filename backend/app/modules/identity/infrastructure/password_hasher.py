"""
Identity infrastructure: Argon2id password hashing
(TRADEOS_TECHNICAL_STACK.md §7.2 — Argon2id, not bcrypt).
"""

from argon2 import PasswordHasher  # type: ignore[import-untyped]
from argon2.exceptions import VerificationError  # type: ignore[import-untyped]

_hasher = PasswordHasher()


def hash_password(raw_password: str) -> str:
    return _hasher.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return bool(_hasher.verify(password_hash, raw_password))
    except VerificationError:
        return False
