"""
Identity infrastructure: SQLAlchemy models for identity.user_accounts
(TRADEOS_DATABASE_DESIGN.md §6.1) and identity.refresh_tokens (Sprint 1.1
extension — see CHANGELOG.md for why this table exists).

Uses SQLAlchemy 2.0's typed `Mapped`/`mapped_column` declarative style
(TRADEOS_TECHNICAL_STACK.md §7.1 — "SQLAlchemy 2.0"), not the legacy
`Column(...)` style: mypy cannot infer a legacy Column's runtime-instance
type, which matters here since repository.py reads these rows straight
back into strictly-typed domain dataclasses.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base


class UserAccountModel(Base):
    __tablename__ = "user_accounts"
    __table_args__ = {"schema": "identity"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "identity"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.user_accounts.id"), nullable=False
    )
    # A hash of the token, never the raw secret — same "never store the
    # secret itself" posture as user_accounts.password_hash.
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
