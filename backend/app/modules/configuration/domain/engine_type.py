"""
Configuration domain: EngineType — TRADEOS_DATABASE_DESIGN.md §6.3.

A data row, not a hardcoded enum, so a sixth engine is addable without a
migration (§7.0). Bias is registered here (Sprint 2.1) as a catalog row
only — it deliberately has no ScoringCriterion/ScoringWeight rows.
See scripts/seed_configuration.py's module docstring and CHANGELOG.md,
Sprint 2.1, for the full reasoning (the Excel's real Bias calculation does
not fit this generic weighted-criteria model — Domain Invariant DI-06/
DI-07 concerns aside, this is deferred to Sprint 3.2 as a design decision,
not silently worked around here).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class EngineType:
    code: str
    display_name: str
    is_signed: bool
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
