"""
Identity presentation: the 4 Authentication endpoints
(TRADEOS_API_SPECIFICATION.md §6.1).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.application.login import LoginUseCase
from app.modules.identity.application.logout import LogoutUseCase
from app.modules.identity.application.refresh import RefreshUseCase
from app.modules.identity.application.register import RegisterUseCase
from app.modules.identity.infrastructure.repository import (
    RefreshTokenRepository,
    UserAccountRepository,
)
from app.modules.identity.presentation.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenPairResponse,
)
from app.modules.preferences.application.create_default_preferences import (
    build_create_default_preferences_use_case,
)
from app.platform.db.session import get_db_session
from app.platform.security.dependencies import get_current_user_id

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, session: AsyncSession = Depends(get_db_session)
) -> RegisterResponse:
    use_case = RegisterUseCase(
        UserAccountRepository(session),
        build_create_default_preferences_use_case(session),
    )
    result = await use_case.execute(payload.email, payload.password)
    await session.commit()
    return RegisterResponse(user_id=result.user_id, email=result.email)


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenPairResponse:
    use_case = LoginUseCase(UserAccountRepository(session), RefreshTokenRepository(session))
    result = await use_case.execute(payload.email, payload.password)
    await session.commit()
    return TokenPairResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=result.expires_in,
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenPairResponse:
    use_case = RefreshUseCase(RefreshTokenRepository(session))
    result = await use_case.execute(payload.refresh_token)
    await session.commit()
    return TokenPairResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=result.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    use_case = LogoutUseCase(RefreshTokenRepository(session))
    await use_case.execute(user_id)
    await session.commit()
