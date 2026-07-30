"""
Playbook infrastructure: SQLAlchemy models for the `playbook` schema
(TRADEOS_DATABASE_DESIGN.md §6.15-6.16, migration 0011).

Typed `Mapped`/`mapped_column` style (SQLAlchemy 2.0), matching every
prior module.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base


class PlaybookSetupModel(Base):
    __tablename__ = "playbook_setups"
    __table_args__ = (
        CheckConstraint("status IN ('active','deprecated')", name="ck_playbook_setups_status"),
        {"schema": "playbook"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("configuration.catalog_entries.id"),
        nullable=False,
        unique=True,
    )
    entry_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")
    exit_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ideal_conditions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risk_rules: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlaybookSetupAttachmentModel(Base):
    __tablename__ = "playbook_setup_attachments"
    __table_args__ = {"schema": "playbook"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playbook_setup_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbook.playbook_setups.id"), nullable=False
    )
    file_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    caption: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
