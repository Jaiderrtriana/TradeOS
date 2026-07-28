"""
Trading domain: TradeMistake — `TRADEOS_DATABASE_DESIGN.md` §6.14, the
many-to-many junction fact between a `Trade` and a Mistake Tag
`CatalogEntry`. No invariants of its own: `kind == mistake_tag` and
active-status validation are Use Case concerns (`TagMistakeUseCase`),
checked against Configuration's own `CatalogEntry`, not re-derived here.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class TradeMistake:
    trade_id: uuid.UUID
    catalog_entry_id: uuid.UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
