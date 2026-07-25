"""
JWT access-token infrastructure — TRADEOS_SYSTEM_ARCHITECTURE.md ADR-07
(token-based authentication via python-jose, TRADEOS_TECHNICAL_STACK.md §7).

Sprint 0.2 scope: only what the authentication middleware needs to verify
an already-issued token. `create_access_token` exists as reusable
infrastructure for the future Login Use Case (Identity module, Phase 1,
TRADEOS_BACKEND_BLUEPRINT.md §4.8) — it is not called from any endpoint in
this sprint. Refresh tokens (TRADEOS_API_SPECIFICATION.md §4.3) belong to
the Identity module's own persistence and are out of scope here.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt  # type: ignore[import-untyped]  # no `types-python-jose` — not adding a package outside the Technical Stack for stubs alone

from app.platform.config import settings


class InvalidTokenError(Exception):
    """Missing, malformed, expired, or invalidly-signed bearer token."""


@dataclass(frozen=True)
class TokenPayload:
    user_id: UUID
    expires_at: datetime | None


def create_access_token(user_id: UUID, expires_delta: timedelta | None = None) -> str:
    """Reusable infrastructure for the future Login Use Case — not exposed by any route yet."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    # API_SPECIFICATION.md §4.2: minimal claims — the authenticated user_id
    # and the token's own expiry, no business data.
    claims = {"sub": str(user_id), "exp": expire}
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload:
    try:
        claims = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError("Invalid or expired token.") from exc

    subject = claims.get("sub")
    if subject is None:
        raise InvalidTokenError("Token is missing its subject claim.")

    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise InvalidTokenError("Token subject is not a valid user id.") from exc

    exp = claims.get("exp")
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp is not None else None
    return TokenPayload(user_id=user_id, expires_at=expires_at)
