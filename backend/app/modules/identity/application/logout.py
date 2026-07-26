"""
LogoutUseCase — TRADEOS_API_SPECIFICATION.md §6.1, POST /auth/logout; §4.4.

The endpoint's contract has no request body — the only identifying data
available is the authenticated caller's user_id (from the verified access
token). There is no way, within that contract, to target one specific
session's refresh token when a user may hold several (e.g., multiple
devices/tabs). Interpreted here as: revoke every currently-active refresh
token for that user. Documented as an implementation interpretation in
CHANGELOG.md, Sprint 1.1 — not a literal instruction from any frozen
document, since none resolves this.
"""

import uuid
from datetime import datetime, timezone

from app.modules.identity.infrastructure.repository import RefreshTokenRepository


class LogoutUseCase:
    def __init__(self, refresh_token_repository: RefreshTokenRepository) -> None:
        self._refresh_tokens = refresh_token_repository

    async def execute(self, user_id: uuid.UUID) -> None:
        await self._refresh_tokens.revoke_all_active_for_user(user_id, datetime.now(timezone.utc))
