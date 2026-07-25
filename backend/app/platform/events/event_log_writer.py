"""
Platform: durably records every published Domain Event into
platform.event_log — the storage-level implementation of Architectural
Principle 5 (Observability Is Not Optional).

Writes into the caller's own session/transaction, never commits itself
(TRADEOS_BACKEND_BLUEPRINT.md §9 — one Use Case, one transaction; §8 —
"if writing an event to platform.event_log fails, the entire transaction
... rolls back").
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db.models import EventLog
from app.platform.events.base import DomainEvent


async def write_to_event_log(event: DomainEvent, session: AsyncSession) -> None:
    session.add(
        EventLog(
            event_type=event.event_type,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            payload=event.payload,
            occurred_at=event.occurred_at,
        )
    )
