"""
Preferences infrastructure: SQLAlchemy model for preferences.user_preferences
(TRADEOS_DATABASE_DESIGN.md §6.2). Typed Mapped/mapped_column style, same
reasoning as Sprint 1.1's identity models.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base


class UserPreferencesModel(Base):
    __tablename__ = "user_preferences"
    __table_args__ = {"schema": "preferences"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Cross-schema FK, explicitly specified by TRADEOS_DATABASE_DESIGN.md §6.2
    # itself ("REFERENCES identity.user_accounts(id)") — a data-integrity
    # relationship, not a code-level module boundary concern.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.user_accounts.id"), nullable=False, unique=True
    )
    theme: Mapped[str] = mapped_column(String(20), nullable=False, default="dark")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="es")
    notification_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
