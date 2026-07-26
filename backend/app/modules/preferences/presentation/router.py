"""
Preferences presentation: GET/PATCH /preferences
(TRADEOS_API_SPECIFICATION.md §6.3). Both require authentication (§6.3:
Auth "Yes") — neither path is in AuthenticationMiddleware's public_paths.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.preferences.application.get_preferences import GetPreferencesUseCase
from app.modules.preferences.application.update_preferences import UpdatePreferencesUseCase
from app.modules.preferences.infrastructure.repository import UserPreferencesRepository
from app.modules.preferences.presentation.schemas import (
    PreferencesResponse,
    UpdatePreferencesRequest,
)
from app.platform.db.session import get_db_session
from app.platform.security.dependencies import get_current_user_id

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=PreferencesResponse)
async def get_preferences(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> PreferencesResponse:
    use_case = GetPreferencesUseCase(UserPreferencesRepository(session))
    preferences = await use_case.execute(user_id)
    return PreferencesResponse(
        theme=preferences.theme,
        language=preferences.language,
        notification_settings=preferences.notification_settings,
    )


@router.patch("", response_model=PreferencesResponse)
async def update_preferences(
    payload: UpdatePreferencesRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> PreferencesResponse:
    use_case = UpdatePreferencesUseCase(UserPreferencesRepository(session))
    preferences = await use_case.execute(
        user_id,
        theme=payload.theme,
        language=payload.language,
        notification_settings=payload.notification_settings,
    )
    await session.commit()
    return PreferencesResponse(
        theme=preferences.theme,
        language=preferences.language,
        notification_settings=preferences.notification_settings,
    )
