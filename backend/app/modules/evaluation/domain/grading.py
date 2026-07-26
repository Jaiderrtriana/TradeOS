"""
Grade derivation shared by Confidence and Quality — factored out here
specifically to avoid duplicating the same "round, then derive a grade"
tail in both `confidence_engine.py` and `quality_engine.py`.

Thresholds are the real values extracted from and approved against
`legacy/Trading Journal v2.0 Stable.xlsx`'s `⚙️ CONFIG` sheet (row 25,
"🏆 UMBRALES DE GRADO", already used to seed Sprint 2.1's Confidence/
Quality data). The Excel itself scopes that row to Confidence and Quality
only (Execution and Market Context have no letter grade in the raw
workbook), but `TRADEOS_DATABASE_DESIGN.md` §6.12 provisions
`execution_grade`/`market_context_grade` columns on the canonical schema
alongside `confidence_grade`/`quality_grade` — Bias is the schema's one
documented exception (signed, no `bias_grade` column at all).

Sprint 3.2 decision (explicit, not a silent Excel replication): every
non-signed engine — Confidence, Quality, Execution, Market Context — is
modeled uniformly as Score + Grade, and `finalize_score` is reused
unchanged for all four rather than introducing a grade-less variant for
two of them. Since no frozen document defines separate thresholds for
Execution/Market Context, these same Confidence/Quality thresholds are
reused for consistency of the canonical domain model, not because the
Excel computes it that way. Replaceable without an architecture change if
a future Product Bible/Excel revision defines engine-specific thresholds.
No frozen document models these as configurable data, so they are
hardcoded domain constants here, not read from any table.
"""

from app.modules.evaluation.domain.rounding import round_half_up
from app.shared_kernel.value_objects import Grade, Score

GRADE_A_PLUS_THRESHOLD = 95.0
GRADE_A_THRESHOLD = 90.0
GRADE_B_THRESHOLD = 80.0
GRADE_C_THRESHOLD = 70.0


def derive_grade(value: float) -> Grade:
    if value >= GRADE_A_PLUS_THRESHOLD:
        return Grade.A_PLUS
    if value >= GRADE_A_THRESHOLD:
        return Grade.A
    if value >= GRADE_B_THRESHOLD:
        return Grade.B
    if value >= GRADE_C_THRESHOLD:
        return Grade.C
    return Grade.D


def finalize_score(raw_score: float) -> Score:
    """Rounds a raw weighted average (`scoring_core.compute_weighted_score`'s
    first return value) with the historically-correct `round_half_up`, and
    derives its Grade — the common tail both Confidence and Quality share."""
    rounded = round_half_up(raw_score)
    return Score(value=rounded, grade=derive_grade(rounded))
