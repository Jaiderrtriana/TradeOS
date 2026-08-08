"""
Unit tests for the access-token infrastructure — encode/decode round trip,
expiry, and signature tampering. No database needed (TRADEOS_DOMAIN_MODEL.md
Section 12.1's "pure function" spirit applies equally here).
"""

import time
from datetime import timedelta
from uuid import uuid4

import pytest
from jose import jwt as jose_jwt  # type: ignore[import-untyped]  # no `types-python-jose` — not adding a package outside the Technical Stack for stubs alone

from app.platform.config import settings
from app.platform.security.jwt import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
)


def test_round_trip_encode_decode():
    user_id = uuid4()
    token = create_access_token(user_id)
    payload = decode_access_token(token)
    assert payload.user_id == user_id
    assert payload.expires_at is not None


def test_expired_token_is_rejected():
    token = create_access_token(uuid4(), expires_delta=timedelta(seconds=-1))
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_tampered_signature_is_rejected():
    token = create_access_token(uuid4())
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered)


def test_token_missing_subject_is_rejected():
    bad_token = jose_jwt.encode(
        {"exp": time.time() + 60}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(bad_token)


def test_token_with_non_uuid_subject_is_rejected():
    bad_token = jose_jwt.encode(
        {"sub": "not-a-uuid", "exp": time.time() + 60},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(bad_token)
