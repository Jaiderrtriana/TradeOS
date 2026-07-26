"""
Configuration domain: ScoringConfigurationVersion — TRADEOS_DOMAIN_MODEL.md
§8.6 (Aggregate Root), TRADEOS_DATABASE_DESIGN.md §6.6.

Versioned, never overwritten (Domain Invariant DI-06/DI-07): a "change" is
always a new row; `status` transitions draft -> published -> superseded.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

DRAFT = "draft"
PUBLISHED = "published"
SUPERSEDED = "superseded"


@dataclass
class ScoringConfigurationVersion:
    version_label: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: str = DRAFT
    published_at: datetime | None = None
    created_by_user_id: uuid.UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
