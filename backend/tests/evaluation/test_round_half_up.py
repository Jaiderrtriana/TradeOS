"""
The historical `round_half_up` regression test — TRADEOS_BACKEND_BLUEPRINT
.md §15's named Deliverable. `48.5 -> 49` is not an invented edge case: it
is Confidence's real raw weighted score for row 2 of
`legacy/Trading Journal v2.0 Stable.xlsx`'s Trades sheet
(|21|*0.5 + 40*0.2 + 100*0.15 + 100*0.15 = 48.5), where Excel's own
`ROUND(48.5, 0)` produces 49 — proof this is the actual historical defect,
not a hypothetical one.
"""

from app.modules.evaluation.domain.rounding import round_half_up


def test_round_half_up_matches_excel_on_the_real_historical_case():
    assert round_half_up(48.5) == 49


def test_python_builtin_round_would_have_silently_reintroduced_the_defect():
    """Documents *why* a dedicated helper exists at all: Python 3's
    built-in `round()` uses round-half-to-even, not Excel's round-half-
    away-from-zero — on this exact real value, they disagree."""
    assert round(48.5) == 48
    assert round_half_up(48.5) != round(48.5)


def test_round_half_up_matches_excel_on_the_second_real_row():
    """Row 3's raw score (39.5) happens to round the same way under both
    strategies (40) — included so both known real cases are protected,
    not just the one that happens to distinguish the two algorithms."""
    assert round_half_up(39.5) == 40


def test_round_half_up_handles_negative_values_away_from_zero():
    assert round_half_up(-2.5) == -3


def test_round_half_up_respects_ndigits():
    assert round_half_up(1.005, ndigits=2) == 1.01
