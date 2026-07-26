"""
Trade Quality engine — the second instance of the generic core
(`scoring_core.py`); net-new this sprint (no reference implementation
covered it). Domain Invariant DI-03 / INV-QUALITY-01: Quality is always
computed independent of a Trade's financial outcome.

This is enforced *structurally*, not just behaviorally: `score_quality`'s
signature has no parameter for P&L, result, or any other financial
outcome, anywhere — there is no value such a parameter could flow through
even if a caller wanted to pass one. `tests/evaluation/test_quality_engine
.py` asserts this directly against the function's own signature.
"""

from app.modules.evaluation.domain.criterion_breakdown_row import CriterionBreakdownRow
from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.modules.evaluation.domain.grading import finalize_score
from app.modules.evaluation.domain.scoring_core import compute_weighted_score
from app.shared_kernel.value_objects import Score


def score_quality(
    criteria: list[EvaluationCriterion],
    weights: list[EvaluationWeight],
    answers: dict[str, str | float],
    profile_code: str,
) -> tuple[Score, list[CriterionBreakdownRow]]:
    raw_score, breakdown = compute_weighted_score(criteria, weights, answers, profile_code)
    return finalize_score(raw_score), breakdown
