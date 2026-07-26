"""
Shared helper: issues a fresh access+refresh token pair.

Used by both LoginUseCase and RefreshUseCase so token issuance has exactly
one implementation, never duplicated per Use Case.
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.modules.identity.domain.refresh_token import RefreshToken
from app.modules.identity.infrastructure.repository import RefreshTokenRepository
from app.modules.identity.infrastructure.token_hasher import hash_token
from app.platform.config import settings
from app.platform.security.jwt import create_access_token


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


async def issue_token_pair(
    user_id: uuid.UUID, refresh_token_repository: RefreshTokenRepository
) -> TokenPair:
    raw_refresh_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    await refresh_token_repository.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=expires_at,
        )
    )

    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=raw_refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )
