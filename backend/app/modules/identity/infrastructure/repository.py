"""
Identity infrastructure: repositories for UserAccount and RefreshToken.

TRADEOS_SYSTEM_ARCHITECTURE.md §3.3: never imported or queried directly
from outside this module.
"""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.refresh_token import RefreshToken
from app.modules.identity.domain.user_account import UserAccount
from app.modules.identity.infrastructure.models import RefreshTokenModel, UserAccountModel


class UserAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> UserAccount | None:
        result = await self._session.execute(
            select(UserAccountModel).where(UserAccountModel.email == email)
        )
        row = result.scalar_one_or_none()
        return _user_to_domain(row) if row is not None else None

    async def get_by_id(self, user_id: uuid.UUID) -> UserAccount | None:
        row = await self._session.get(UserAccountModel, user_id)
        return _user_to_domain(row) if row is not None else None

    async def add(self, user: UserAccount) -> None:
        self._session.add(
            UserAccountModel(
                id=user.id,
                email=user.email,
                password_hash=user.password_hash,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        )


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> None:
        self._session.add(
            RefreshTokenModel(
                id=token.id,
                user_id=token.user_id,
                token_hash=token.token_hash,
                issued_at=token.issued_at,
                expires_at=token.expires_at,
                revoked_at=token.revoked_at,
            )
        )

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        row = result.scalar_one_or_none()
        return _refresh_token_to_domain(row) if row is not None else None

    async def revoke(self, token_id: uuid.UUID, revoked_at: datetime) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.id == token_id)
            .values(revoked_at=revoked_at)
        )

    async def revoke_all_active_for_user(self, user_id: uuid.UUID, revoked_at: datetime) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id, RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )


def _user_to_domain(row: UserAccountModel) -> UserAccount:
    return UserAccount(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _refresh_token_to_domain(row: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        issued_at=row.issued_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
    )
