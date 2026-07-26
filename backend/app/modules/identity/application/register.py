"""
RegisterUseCase — TRADEOS_BACKEND_BLUEPRINT.md §4.8;
TRADEOS_API_SPECIFICATION.md §6.1, POST /auth/register.
"""

from dataclasses import dataclass

from app.modules.identity.domain.user_account import UserAccount
from app.modules.identity.infrastructure.password_hasher import hash_password
from app.modules.identity.infrastructure.repository import UserAccountRepository
from app.platform.errors import ConflictError


@dataclass(frozen=True)
class RegisterResult:
    user_id: str
    email: str


class RegisterUseCase:
    def __init__(self, repository: UserAccountRepository) -> None:
        self._repository = repository

    async def execute(self, email: str, password: str) -> RegisterResult:
        existing = await self._repository.get_by_email(email)
        if existing is not None:
            raise ConflictError("An account with this email already exists.")

        user = UserAccount(email=email, password_hash=hash_password(password))
        await self._repository.add(user)
        return RegisterResult(user_id=str(user.id), email=user.email)
