"""
Execution Score engine — the third instance of the generic core
(`scoring_core.py`). No engine-specific transform needed (unlike
Confidence's `ABS()`): all four real criteria (Entry Timing, Stop
Placement, TP Execution, Management) are category-mapped, unsigned,
profile-independent, exactly like Quality.

Reuses `finalize_score` unchanged, so this engine's Score does carry a
Grade — even though the real Excel has no letter-grade thresholds for
Execution. See `grading.py`'s docstring for the Sprint 3.2 decision:
every non-signed engine is modeled uniformly as Score + Grade, per
`TRADEOS_DATABASE_DESIGN.md` §6.12's `execution_grade` column, reusing
Confidence/Quality's thresholds for consistency rather than inventing
Execution-specific ones with no source data.
"""

from app.modules.evaluation.domain.criterion_breakdown_row import CriterionBreakdownRow
from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.modules.evaluation.domain.grading import finalize_score
from app.modules.evaluation.domain.scoring_core import compute_weighted_score
from app.shared_kernel.value_objects import Score


def score_execution(
    criteria: list[EvaluationCriterion],
    weights: list[EvaluationWeight],
    answers: dict[str, str | float],
    profile_code: str,
) -> tuple[Score, list[CriterionBreakdownRow]]:
    raw_score, breakdown = compute_weighted_score(criteria, weights, answers, profile_code)
    return finalize_score(raw_score), breakdown
