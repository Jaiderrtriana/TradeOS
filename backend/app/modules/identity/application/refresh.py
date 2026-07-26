"""
RefreshUseCase — TRADEOS_API_SPECIFICATION.md §6.1, POST /auth/refresh;
§4.3: single-use rotation. The presented refresh token is revoked
immediately upon use, before a new pair is issued — a revoked, expired, or
unknown token is rejected identically (401 UNAUTHENTICATED), which is what
makes reuse of an already-rotated token detectable and rejected.
"""

from datetime import datetime, timezone

from app.modules.identity.application.token_issuance import TokenPair, issue_token_pair
from app.modules.identity.infrastructure.repository import RefreshTokenRepository
from app.modules.identity.infrastructure.token_hasher import hash_token
from app.platform.errors import UnauthenticatedError


class RefreshUseCase:
    def __init__(self, refresh_token_repository: RefreshTokenRepository) -> None:
        self._refresh_tokens = refresh_token_repository

    async def execute(self, raw_refresh_token: str) -> TokenPair:
        token = await self._refresh_tokens.get_by_token_hash(hash_token(raw_refresh_token))

        if token is None or not token.is_valid():
            raise UnauthenticatedError("Refresh token is invalid, expired, or already used.")

        await self._refresh_tokens.revoke(token.id, datetime.now(timezone.utc))

        return await issue_token_pair(token.user_id, self._refresh_tokens)
