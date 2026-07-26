"""
Evaluation domain: EvaluationCriterion — Evaluation's OWN input shape, not
`app.modules.configuration.domain.scoring_criterion.ScoringCriterion`.

TRADEOS_SYSTEM_ARCHITECTURE.md §3.3 (Forbidden Dependencies): a module may
never import another module's domain layer directly. The real translation
from Configuration's persisted `ScoringCriterion` rows into this shape is
Sprint 3.2's `PreviewEvaluation` Use Case's job (Application layer) — this
module's domain layer stays decoupled and independently testable, exactly
per this sprint's approved scope (zero infrastructure, zero wiring to
Configuration).
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvaluationCriterion:
    id: str
    name: str
    min_value: float
    max_value: float
    # Label -> normalized sub-score (0-100), e.g. {"Full Alignment": 100}.
    # None for a purely numeric criterion, normalized via min/max instead
    # (TRADEOS_DATABASE_DESIGN.md §6.5).
    category_map: dict[str, Any] | None = None
