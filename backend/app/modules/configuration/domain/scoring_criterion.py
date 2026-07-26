"""
Configuration domain: ScoringCriterion — TRADEOS_DOMAIN_MODEL.md §8.4,
TRADEOS_DATABASE_DESIGN.md §6.5.

`id` is a stable, human-assigned string slug (never a UUID) — DB Design
§2.4.1's one documented exception, required by Domain Invariant
INV-CRITERION-01 ("identified by stable ID, never row position").
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ScoringCriterion:
    id: str
    engine_type_code: str
    name: str
    source_field: str
    min_value: float
    max_value: float
    category: str | None = None
    description: str = ""
    category_map: dict[str, Any] | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
