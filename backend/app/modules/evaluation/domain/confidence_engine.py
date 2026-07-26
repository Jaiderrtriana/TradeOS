"""
Trade Confidence engine — one of the five instances of the generic core
(`scoring_core.py`), per `PROJECT_AUDIT.md` §3.2. The only thing specific
to Confidence, beyond which criteria/weights it's called with, is that its
`bias_index_at_entry` criterion is scored on the *absolute* value of the
(signed) Bias Index — exactly `ROUND(ABS(AF2)*W_CONF_BIAS + ..., 0)` in
the real Excel formula. That `ABS()` is Confidence's own business rule,
not a generic normalization concern (a future signed engine like Bias
must NOT have it applied), so it is handled here, immediately before
calling the shared core, rather than inside `scoring_core.py`.
"""

from app.modules.evaluation.domain.criterion_breakdown_row import CriterionBreakdownRow
from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.modules.evaluation.domain.grading import finalize_score
from app.modules.evaluation.domain.scoring_core import compute_weighted_score
from app.shared_kernel.value_objects import Score

# The stable criterion ID Sprint 2.1 seeded for this criterion
# (scripts/seed_configuration.py) — referenced by ID, per
# INV-CRITERION-01 ("identified by stable ID, never row position"), not
# by any assumption about ordering or position in the `criteria` list.
BIAS_INDEX_CRITERION_ID = "confidence.bias_index_at_entry"


def score_confidence(
    criteria: list[EvaluationCriterion],
    weights: list[EvaluationWeight],
    answers: dict[str, str | float],
    profile_code: str,
) -> tuple[Score, list[CriterionBreakdownRow]]:
    adjusted_answers = dict(answers)
    if BIAS_INDEX_CRITERION_ID in adjusted_answers:
        adjusted_answers[BIAS_INDEX_CRITERION_ID] = abs(
            float(adjusted_answers[BIAS_INDEX_CRITERION_ID])
        )

    raw_score, breakdown = compute_weighted_score(criteria, weights, adjusted_answers, profile_code)
    return finalize_score(raw_score), breakdown
