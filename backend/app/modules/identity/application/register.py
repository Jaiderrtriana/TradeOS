"""
RegisterUseCase — TRADEOS_BACKEND_BLUEPRINT.md §4.8;
TRADEOS_API_SPECIFICATION.md §6.1, POST /auth/register.

Sprint 1.2: also creates default UserPreferences in the same transaction
(§6.3: "created automatically with defaults at registration") by calling
Preferences' published Application-layer factory — never importing
Preferences' infrastructure layer directly
(TRADEOS_SYSTEM_ARCHITECTURE.md §3.3). See CHANGELOG.md, Sprint 1.2, for
the full reasoning behind this cross-module call.
"""

from dataclasses import dataclass

from app.modules.identity.domain.user_account import UserAccount
from app.modules.identity.infrastructure.password_hasher import hash_password
from app.modules.identity.infrastructure.repository import UserAccountRepository
from app.modules.preferences.application.create_default_preferences import (
    CreateDefaultPreferencesUseCase,
)
from app.platform.errors import ConflictError


@dataclass(frozen=True)
class RegisterResult:
    user_id: str
    email: str


class RegisterUseCase:
    def __init__(
        self,
        repository: UserAccountRepository,
        create_default_preferences_use_case: CreateDefaultPreferencesUseCase,
    ) -> None:
        self._repository = repository
        self._create_default_preferences = create_default_preferences_use_case

    async def execute(self, email: str, password: str) -> RegisterResult:
        existing = await self._repository.get_by_email(email)
        if existing is not None:
            raise ConflictError("An account with this email already exists.")

        user = UserAccount(email=email, password_hash=hash_password(password))
        await self._repository.add(user)
        await self._create_default_preferences.execute(user.id)

        return RegisterResult(user_id=str(user.id), email=user.email)
