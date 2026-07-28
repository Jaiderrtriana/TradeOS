"""
Platform: the event_log table.

Durable record of every Domain Event as it fires — the storage-level
implementation of Architectural Principle 5 (Observability Is Not Optional,
TRADEOS_SYSTEM_ARCHITECTURE.md §1). Append-only, forever: never updated,
never deleted (TRADEOS_DATABASE_DESIGN.md §6.18).
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base


class EventLog(Base):
    __tablename__ = "event_log"
    __table_args__ = (
        Index("ix_event_log_aggregate_type_aggregate_id", "aggregate_type", "aggregate_id"),
        Index("ix_event_log_event_type", "event_type"),
        Index("ix_event_log_occurred_at", "occurred_at"),
        {"schema": "platform"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(60), nullable=False)
    # Deliberately not a foreign key — the referenced row may later be soft-
    # deleted or live in a different schema than the event log expects; an
    # event must remain readable regardless (TRADEOS_DATABASE_DESIGN.md §6.18).
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class IdempotencyKeyModel(Base):
    """`app/platform/idempotency.py`'s persistence — see that module for
    the full claim/replay design (migration 0008, Sprint 4.1)."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        Index("ix_idempotency_keys_user_key", "user_id", "idempotency_key", unique=True),
        {"schema": "platform"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.user_accounts.id"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
