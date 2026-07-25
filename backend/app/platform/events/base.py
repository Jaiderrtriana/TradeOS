"""
Platform: the Domain Event shape every module publishes against.

Deliberately generic and minimal — TRADEOS_DOMAIN_MODEL.md §11 names the
concrete event catalog (TradeRegistered, TradeEvaluated, ...), but no
concrete event is introduced until the module that raises it is built
(Trading in Phase 4, Configuration in Phase 2, etc.). Sprint 0.1 only needs
the shape the dispatcher and event_log writer operate on.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    aggregate_type: str
    aggregate_id: uuid.UUID
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
