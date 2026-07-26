"""
CreateDefaultPreferencesUseCase — TRADEOS_API_SPECIFICATION.md §6.3:
"Created automatically with defaults at registration."

Approved design (Sprint 1.2): Identity's RegisterUseCase calls this Use
Case synchronously, in the same transaction as the UserAccount insert —
the same pattern already established for Trading -> Evaluation
(TRADEOS_SYSTEM_ARCHITECTURE.md §4, ADR-03). See CHANGELOG.md, Sprint 1.2,
for why this cross-module call exists (no `UserRegistered` Domain Event is
defined anywhere in TRADEOS_DOMAIN_MODEL.md §11 to hook into instead).
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.preferences.domain.user_preferences import UserPreferences
from app.modules.preferences.infrastructure.repository import UserPreferencesRepository


class CreateDefaultPreferencesUseCase:
    def __init__(self, repository: UserPreferencesRepository) -> None:
        self._repository = repository

    async def execute(self, user_id: uuid.UUID) -> None:
        await self._repository.add(UserPreferences(user_id=user_id))


def build_create_default_preferences_use_case(
    session: AsyncSession,
) -> CreateDefaultPreferencesUseCase:
    """
    Factory exposed so other modules (Identity's RegisterUseCase) can wire
    this Use Case without ever importing Preferences' infrastructure layer
    directly (TRADEOS_SYSTEM_ARCHITECTURE.md §3.3, Forbidden Dependencies)
    — a module's published contract is its Application layer only.
    """
    return CreateDefaultPreferencesUseCase(UserPreferencesRepository(session))
