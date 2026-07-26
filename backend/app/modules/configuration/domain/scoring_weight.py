"""Configuration domain: ScoringWeight — TRADEOS_DOMAIN_MODEL.md §8.5,
TRADEOS_DATABASE_DESIGN.md §6.7."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ScoringWeight:
    configuration_version_id: uuid.UUID
    criterion_id: str
    profile_code: str
    weight: float
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
