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
with signed category-map values instead of Confidence/Quality/Execution/
Market Context's unsigned ones. `scoring_core.py` required zero changes
to support this — every Bias
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

**BIAS_SCALE_FACTOR (Sprint 3.2, real Bias data proposal, decision #5):**
the real Bias data (`scripts/seed_configuration.py`, `BIAS_CRITERIA`) uses
category-map point values taken directly from the Excel (mostly -4..+4,
a few down to -5). With `BIAS_WEIGHT = 1/35` applied equally to all 35
active criteria, the resulting weighted average — the same math as every
other engine's average, just signed — naturally lands in roughly -5..+5,
not the Excel UI's -100..+100 (which the raw Excel reaches only via the
fixed 38/45 divisor `scoring_core.py` deliberately doesn't reproduce, per
Camino A). To keep a consistent, comparable experience across the five
engines' scores, the raw weighted average is rescaled by this single,
isolated constant before rounding — nowhere else: not in
`scoring_core.py` (kept fully generic, this constant has meaning only for
Bias's specific category-map data), not in Configuration's schema or
seed data (the constant is a display/comparability decision, not
business data). Replace this single line, with no other code change, if
a future revision of the real Excel data changes the natural range, or
if the definitive Bias Engine model (a future sprint) supersedes this
entirely.
"""

from app.modules.evaluation.domain.criterion_breakdown_row import CriterionBreakdownRow
from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.modules.evaluation.domain.rounding import round_half_up
from app.modules.evaluation.domain.scoring_core import compute_weighted_score
from app.shared_kernel.value_objects import Score

# Isolated to this engine only (see module docstring). A round, simple,
# explicit constant -- not derived from any real Excel formula -- chosen
# so the real seeded data's natural weighted-average range (roughly
# -5..+5) reads on a comparable, roughly -100..100 scale to the other
# four engines' 0-100 scores. Replace this single line if the underlying
# Bias data or its intended display range ever changes.
BIAS_SCALE_FACTOR = 20


def score_bias(
    criteria: list[EvaluationCriterion],
    weights: list[EvaluationWeight],
    answers: dict[str, str | float],
    profile_code: str,
) -> tuple[Score, list[CriterionBreakdownRow]]:
    raw_score, breakdown = compute_weighted_score(criteria, weights, answers, profile_code)
    scaled_score = raw_score * BIAS_SCALE_FACTOR
    return Score(value=round_half_up(scaled_score), grade=None), breakdown
