"""
LoginUseCase — TRADEOS_API_SPECIFICATION.md §6.1, POST /auth/login;
§4.1 (access+refresh pair).
"""

from app.modules.identity.application.token_issuance import TokenPair, issue_token_pair
from app.modules.identity.infrastructure.password_hasher import verify_password
from app.modules.identity.infrastructure.repository import (
    RefreshTokenRepository,
    UserAccountRepository,
)
from app.platform.errors import UnauthenticatedError


class LoginUseCase:
    def __init__(
        self,
        user_repository: UserAccountRepository,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        self._users = user_repository
        self._refresh_tokens = refresh_token_repository

    async def execute(self, email: str, password: str) -> TokenPair:
        user = await self._users.get_by_email(email)

        # Deliberately identical error whether the email doesn't exist or
        # the password is wrong (API Spec §6.1) — never confirm which
        # emails are registered.
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthenticatedError("Invalid email or password.")

        return await issue_token_pair(user.id, self._refresh_tokens)
