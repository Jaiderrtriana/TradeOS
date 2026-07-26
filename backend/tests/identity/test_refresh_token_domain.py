from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.modules.identity.domain.refresh_token import RefreshToken


def _make_token(expires_delta: timedelta, revoked: bool = False) -> RefreshToken:
    token = RefreshToken(
        user_id=uuid4(),
        token_hash="hash",
        expires_at=datetime.now(timezone.utc) + expires_delta,
    )
    if revoked:
        token.revoke()
    return token


def test_valid_token_is_valid():
    assert _make_token(timedelta(days=1)).is_valid() is True


def test_expired_token_is_invalid():
    assert _make_token(timedelta(days=-1)).is_valid() is False


def test_revoked_token_is_invalid():
    assert _make_token(timedelta(days=1), revoked=True).is_valid() is False
