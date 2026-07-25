"""
Proves Sprint 0.1's Exit Criteria (TRADEOS_IMPLEMENTATION_MASTER_PLAN.md,
Phase 0, Sprint 0.1): a synthetic event published by a throwaway test
handler is durably recorded in platform.event_log and visible via a direct
query.
"""

import uuid

from sqlalchemy import select

from app.platform.db.models import EventLog
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher


async def test_published_event_is_durably_recorded_and_queryable(db_session):
    dispatcher = EventDispatcher()
    handled_events = []

    async def throwaway_handler(event: DomainEvent, session) -> None:
        handled_events.append(event)

    dispatcher.subscribe("TestEvent", throwaway_handler)

    aggregate_id = uuid.uuid4()
    event = DomainEvent(
        event_type="TestEvent",
        aggregate_type="TestAggregate",
        aggregate_id=aggregate_id,
        payload={"example": "value"},
    )

    await dispatcher.publish(event, db_session)
    await db_session.commit()

    # The subscribe/publish path itself was exercised, not just the log write.
    assert len(handled_events) == 1
    assert handled_events[0] is event

    # A direct query, independent of the dispatcher, proves durability.
    result = await db_session.execute(select(EventLog).where(EventLog.aggregate_id == aggregate_id))
    row = result.scalar_one()
    assert row.event_type == "TestEvent"
    assert row.aggregate_type == "TestAggregate"
    assert row.payload == {"example": "value"}
    assert row.occurred_at is not None
