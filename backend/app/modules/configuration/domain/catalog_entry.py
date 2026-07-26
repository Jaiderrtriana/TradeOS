"""
Configuration domain: CatalogEntry — TRADEOS_DOMAIN_MODEL.md §8.7,
TRADEOS_DATABASE_DESIGN.md §6.8.

"name, kind, and is_active are, today, the complete confirmed shape of a
catalog entry" (§6.8) — no description, no metadata beyond this.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

SETUP = "setup"
SESSION = "session"
STRATEGY = "strategy"
ENTRY_TRIGGER = "entry_trigger"
MISTAKE_TAG = "mistake_tag"

VALID_KINDS = frozenset({SETUP, SESSION, STRATEGY, ENTRY_TRIGGER, MISTAKE_TAG})


@dataclass
class CatalogEntry:
    kind: str
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
