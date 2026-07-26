"""
Grade derivation shared by Confidence and Quality — factored out here
specifically to avoid duplicating the same "round, then derive a grade"
tail in both `confidence_engine.py` and `quality_engine.py`.

Thresholds are the real values extracted from and approved against
`legacy/Trading Journal v2.0 Stable.xlsx`'s `⚙️ CONFIG` sheet (row 25,
"🏆 UMBRALES DE GRADO", already used to seed Sprint 2.1's Confidence/
Quality data) — applicable to Confidence and Quality only, per that same
sheet's own scope ("aplica a Confidence y Quality"; Execution and Market
Context have no letter grade in the Excel, and Bias, being signed, has
none either, TRADEOS_DATABASE_DESIGN.md §6.12). No frozen document models
these as configurable data, so they are hardcoded domain constants here,
not read from any table.
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
