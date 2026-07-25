"""
Platform: the event_log table.

Durable record of every Domain Event as it fires — the storage-level
implementation of Architectural Principle 5 (Observability Is Not Optional,
TRADEOS_SYSTEM_ARCHITECTURE.md §1). Append-only, forever: never updated,
never deleted (TRADEOS_DATABASE_DESIGN.md §6.18).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.platform.db.base import Base


class EventLog(Base):
    __tablename__ = "event_log"
    __table_args__ = (
        Index("ix_event_log_aggregate_type_aggregate_id", "aggregate_type", "aggregate_id"),
        Index("ix_event_log_event_type", "event_type"),
        Index("ix_event_log_occurred_at", "occurred_at"),
        {"schema": "platform"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(60), nullable=False)
    aggregate_type = Column(String(60), nullable=False)
    # Deliberately not a foreign key — the referenced row may later be soft-
    # deleted or live in a different schema than the event log expects; an
    # event must remain readable regardless (TRADEOS_DATABASE_DESIGN.md §6.18).
    aggregate_id = Column(UUID(as_uuid=True), nullable=False)
    payload = Column(JSONB, nullable=False)
    occurred_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
