"""
Trading domain: ChecklistSnapshot — `TRADEOS_DATABASE_DESIGN.md` §6.10,
`TRADEOS_DOMAIN_MODEL.md` §8.2. The raw checklist answers a Trade was
registered with, frozen at registration time — "a snapshot, because the
Checklist Engine's *definitions* (source_field set) may evolve later
without rewriting history" (§6.10).
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ChecklistSnapshot:
    trade_id: uuid.UUID
    answers: dict[str, str | float]
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
