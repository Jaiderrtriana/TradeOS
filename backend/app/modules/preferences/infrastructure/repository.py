"""
Preferences infrastructure: UserPreferencesRepository.

TRADEOS_SYSTEM_ARCHITECTURE.md §3.3: never imported or queried directly
from outside this module — other modules (Identity) reach this only
through app/modules/preferences/application's published factory
(see create_default_preferences.py).
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.preferences.domain.user_preferences import UserPreferences
from app.modules.preferences.infrastructure.models import UserPreferencesModel


class UserPreferencesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserPreferences | None:
        result = await self._session.execute(
            select(UserPreferencesModel).where(UserPreferencesModel.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row is not None else None

    async def add(self, preferences: UserPreferences) -> None:
        self._session.add(
            UserPreferencesModel(
                id=preferences.id,
                user_id=preferences.user_id,
                theme=preferences.theme,
                language=preferences.language,
                notification_settings=preferences.notification_settings,
                created_at=preferences.created_at,
                updated_at=preferences.updated_at,
            )
        )

    async def update(self, preferences: UserPreferences) -> None:
        await self._session.execute(
            update(UserPreferencesModel)
            .where(UserPreferencesModel.user_id == preferences.user_id)
            .values(
                theme=preferences.theme,
                language=preferences.language,
                notification_settings=preferences.notification_settings,
                updated_at=preferences.updated_at,
            )
        )


def _to_domain(row: UserPreferencesModel) -> UserPreferences:
    return UserPreferences(
        id=row.id,
        user_id=row.user_id,
        theme=row.theme,
        language=row.language,
        notification_settings=row.notification_settings,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
