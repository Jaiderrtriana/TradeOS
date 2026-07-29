"""
Journal domain: JournalEntry — Aggregate Root (`TRADEOS_DOMAIN_MODEL.md`
§8.10): "free-text qualitative reflection, either attached to a specific
Trade or to a period (e.g., a week)... either a Trade reference or a
date-range reference (never both)."

No computed properties, no lifecycle beyond create/edit/soft-delete — the
Domain Model names none, and `TRADEOS_DOMAIN_MODEL.md` §11 (Business
Events) and §14-15 (Domain Invariants) name no event and no numbered
invariant for Journal. `validate_exactly_one_reference` mirrors the same
"raise from `__post_init__`, reuse the same function on amendment"
pattern `trading/domain/trade.py`'s `validate_stop_placement` already
established — reused here despite this being a genuinely new pattern in
this codebase (a mutual-exclusivity check between two possible
references, not a single-field range check), because the *shape* of the
pattern (a free function, called from both construction and any future
update path) is what's being reused, not any Trading-specific logic.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from app.platform.errors import UnprocessableEntityError


def validate_exactly_one_reference(
    trade_id: uuid.UUID | None, period_start: date | None, period_end: date | None
) -> None:
    """`TRADEOS_DATABASE_DESIGN.md` §6.17's check constraint, realized in
    the domain layer: exactly one of `trade_id` or (`period_start` AND
    `period_end`) — never both, never neither. No numbered Domain
    Invariant exists for this (confirmed absent from
    `TRADEOS_DOMAIN_MODEL.md` §14-15), so this raises the same
    `UnprocessableEntityError` / `UNPROCESSABLE_ENTITY` shape
    `TagMistakeUseCase` already established for a business rule with no
    numbered invariant (Sprint 4.3) — not `VALIDATION_FAILED`, since this
    is a cross-field business rule, not a single-field shape check."""
    has_trade = trade_id is not None
    has_period = period_start is not None or period_end is not None
    if has_trade and has_period:
        raise UnprocessableEntityError(
            "A journal entry may reference a Trade or a period, never both."
        )
    if not has_trade and not has_period:
        raise UnprocessableEntityError("A journal entry must reference either a Trade or a period.")
    if has_period and (period_start is None or period_end is None):
        raise UnprocessableEntityError(
            "A period-scoped journal entry requires both period_start and period_end."
        )


@dataclass
class JournalEntry:
    user_id: uuid.UUID
    content: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    trade_id: uuid.UUID | None = None
    period_start: date | None = None
    period_end: date | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        validate_exactly_one_reference(self.trade_id, self.period_start, self.period_end)
