"""
Bias Index engine — the fifth and final instance of the generic core.

**Camino A (approved decision, Sprint 3.2):** `TRADEOS_PRODUCT_BIBLE.md`
§8.2 — "the single most important part of this document... binding on
every future technical document" — states Principle 5 (self-normalizing
aggregation: divide by the sum of active weights, never a fixed constant)
and Principle 7 (weights, not category maps, vary by profile) as holding
for all five engines; Principle 4 separates Bias from the other four only
on the *sign* of its normalized values, never on the aggregation formula.
This engine follows that binding text exactly: it calls the exact same,
unmodified `scoring_core.compute_weighted_score` every other engine uses,
with signed category-map values (e.g. a -100..100 range) instead of
Confidence/Quality/Execution/Market Context's unsigned 0..100 ones.
`scoring_core.py` required zero changes to support this — every Bias
criterion is categorical (never a raw numeric range) in the real Excel,
so this never exercises `normalize()`'s min/max path, which is the one
place a signed range could have been mishandled (it unconditionally
rescales to a *positive* 0-100 span).

**Known, documented divergence from the real Excel — not fixed here:**
the actual `legacy/Trading Journal v2.0 Stable.xlsx` Bias Index divides by
a fixed per-profile constant (38 or 45) and its category-to-point mapping
itself changes by profile, neither of which this generic, Product-Bible-
compliant implementation reproduces. Registered as known technical debt
(Sprint 2.1, reaffirmed Sprint 3.2) — the Excel is not treated as the
tie-breaker here; the canonical, binding Product Bible is.

Domain Invariant DI-05: Bias is the *only* signed engine — realized here
by never deriving a Grade (TRADEOS_DATABASE_DESIGN.md §6.12: no
`bias_grade` column; "a directional score does not map to a quality
grade"). Unlike every unsigned engine (which all funnel through
`grading.finalize_score`), Bias's own finalization is inlined below
rather than reusing that helper, specifically so it structurally cannot
acquire a Grade by accident.
"""

from app.modules.evaluation.domain.criterion_breakdown_row import CriterionBreakdownRow
from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.modules.evaluation.domain.rounding import round_half_up
from app.modules.evaluation.domain.scoring_core import compute_weighted_score
from app.shared_kernel.value_objects import Score


def score_bias(
    criteria: list[EvaluationCriterion],
    weights: list[EvaluationWeight],
    answers: dict[str, str | float],
    profile_code: str,
) -> tuple[Score, list[CriterionBreakdownRow]]:
    raw_score, breakdown = compute_weighted_score(criteria, weights, answers, profile_code)
    return Score(value=round_half_up(raw_score), grade=None), breakdown
