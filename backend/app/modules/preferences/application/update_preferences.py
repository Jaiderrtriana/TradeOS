"""
UpdatePreferencesUseCase — TRADEOS_API_SPECIFICATION.md §6.3, PATCH
/preferences. "No business validation beyond allowed enum values for
theme/language" — enum membership itself is enforced at the Presentation
layer (Pydantic Literal types, shape validation), not here.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from app.modules.preferences.domain.user_preferences import UserPreferences
from app.modules.preferences.infrastructure.repository import UserPreferencesRepository


class UpdatePreferencesUseCase:
    def __init__(self, repository: UserPreferencesRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        user_id: uuid.UUID,
        theme: str | None = None,
        language: str | None = None,
        notification_settings: dict[str, Any] | None = None,
        timezone_: str | None = None,
    ) -> UserPreferences:
        preferences = await self._repository.get_by_user_id(user_id)
        if preferences is None:
            raise RuntimeError(
                f"UserPreferences missing for user_id={user_id}; registration invariant violated."
            )

        if theme is not None:
            preferences.theme = theme
        if language is not None:
            preferences.language = language
        if notification_settings is not None:
            preferences.notification_settings = notification_settings
        if timezone_ is not None:
            preferences.timezone = timezone_
        preferences.updated_at = datetime.now(timezone.utc)

        await self._repository.update(preferences)
        return preferences
