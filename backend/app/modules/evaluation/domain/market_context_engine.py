"""
Market Context Score engine — the fourth instance of the generic core.
Its 30 real criteria (Sprint 2.1) are all numeric ranges (no
`category_map`), the first real exercise of `scoring_core.normalize()`'s
min/max rescaling path prepared ahead of time in Sprint 3.1.

Domain Invariant DI-04 / INV-CONTEXT-01: Market Context is always
computed independent of Bias's direction. Enforced structurally, exactly
like DI-03 for Quality: `score_market_context`'s signature has no
parameter shaped like a Bias score or direction anywhere —
`tests/evaluation/test_market_context_engine.py` asserts this directly
against the function's own signature.

Reuses `finalize_score` unchanged, so this engine's Score does carry a
Grade — even though the real Excel has no letter-grade thresholds for
Market Context. See `grading.py`'s docstring for the Sprint 3.2 decision:
every non-signed engine is modeled uniformly as Score + Grade, per
`TRADEOS_DATABASE_DESIGN.md` §6.12's `market_context_grade` column,
reusing Confidence/Quality's thresholds for consistency rather than
inventing Market-Context-specific ones with no source data.
"""

from app.modules.evaluation.domain.criterion_breakdown_row import CriterionBreakdownRow
from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.modules.evaluation.domain.grading import finalize_score
from app.modules.evaluation.domain.scoring_core import compute_weighted_score
from app.shared_kernel.value_objects import Score


def score_market_context(
    criteria: list[EvaluationCriterion],
    weights: list[EvaluationWeight],
    answers: dict[str, str | float],
    profile_code: str,
) -> tuple[Score, list[CriterionBreakdownRow]]:
    raw_score, breakdown = compute_weighted_score(criteria, weights, answers, profile_code)
    return finalize_score(raw_score), breakdown
