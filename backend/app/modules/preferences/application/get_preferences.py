"""
GetPreferencesUseCase — TRADEOS_API_SPECIFICATION.md §6.3, GET /preferences.
"""

import uuid

from app.modules.preferences.domain.user_preferences import UserPreferences
from app.modules.preferences.infrastructure.repository import UserPreferencesRepository


class GetPreferencesUseCase:
    def __init__(self, repository: UserPreferencesRepository) -> None:
        self._repository = repository

    async def execute(self, user_id: uuid.UUID) -> UserPreferences:
        preferences = await self._repository.get_by_user_id(user_id)
        if preferences is None:
            # API Spec §6.3 guarantees this endpoint "never 404s for an
            # authenticated user" because CreateDefaultPreferencesUseCase
            # runs atomically at registration. Reaching this means that
            # invariant was violated (e.g., data corruption) — a genuine
            # bug, deliberately not modeled as a documented 404 the spec
            # does not define for this endpoint.
            raise RuntimeError(
                f"UserPreferences missing for user_id={user_id}; registration invariant violated."
            )
        return preferences
