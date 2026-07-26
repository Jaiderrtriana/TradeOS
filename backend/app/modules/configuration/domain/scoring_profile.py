"""Configuration domain: ScoringProfile — TRADEOS_DATABASE_DESIGN.md §6.4."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ScoringProfile:
    code: str
    display_name: str
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
