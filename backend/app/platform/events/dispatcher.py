"""
Platform: the in-process, synchronous Domain Event dispatcher.

TRADEOS_SYSTEM_ARCHITECTURE.md §6.1 — an event is published by the module
whose action caused it, immediately after that action completes, within the
same request and the same database transaction; any subscribing module's
handler runs synchronously, in the same request. No external message broker
exists in v1 (§6.3, ADR-05) — this in-process dispatcher is the exact seam
that becomes an async bus later, without any publishing module changing.

Every published event is unconditionally recorded to platform.event_log
first (TRADEOS_DATABASE_DESIGN.md §6.18) — durability does not depend on
whether any module currently subscribes to that event type
(TRADEOS_API_SPECIFICATION.md §11: "No consumer currently subscribes ...
they are logged for future consumers").
"""

from collections import defaultdict
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.events.base import DomainEvent
from app.platform.events.event_log_writer import write_to_event_log

EventHandler = Callable[[DomainEvent, AsyncSession], Awaitable[None]]


class EventDispatcher:
    """Stateless in the business sense — holds only handler registrations."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, event: DomainEvent, session: AsyncSession) -> None:
        await write_to_event_log(event, session)
        for handler in self._subscribers.get(event.event_type, []):
            await handler(event, session)


# One dispatcher instance for the whole process — every module publishes
# through this same instance (wired at startup in app/main.py).
dispatcher = EventDispatcher()
