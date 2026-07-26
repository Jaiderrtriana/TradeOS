"""
Market Context engine tests. Unlike Confidence/Quality/Execution, the
Trades sheet only stores the final "Market Context Score Entry" per
historical trade (53 and 52 for rows 2/3), never the 30 raw checklist
inputs that produced it (those live transiently in the CHECKLIST sheet,
not persisted per-trade) — so no fully independent "known input -> known
output" case can be reconstructed the way it could for the other three
engines. Instead, this uses a representative subset of the real Sprint
2.1 criteria/weights (exact ranges and Day Trading weights from
scripts/seed_configuration.py) with a hand-computed expected result, plus
the mandatory structural DI-04 test.
"""

import inspect

from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.modules.evaluation.domain.market_context_engine import score_market_context

PROFILE = "day_trading"

# A representative subset of the real 30 Market Context criteria
# (exact id/range/weight from scripts/seed_configuration.py).
CRITERIA = [
    EvaluationCriterion(
        id="market_context.dxy", name="DXY — Dollar Index", min_value=-4, max_value=4
    ),
    EvaluationCriterion(id="market_context.spy", name="SPY / TradFi", min_value=-4, max_value=3),
    EvaluationCriterion(
        id="market_context.atr", name="ATR / Volatilidad", min_value=-1, max_value=2
    ),
    EvaluationCriterion(
        id="market_context.confluence",
        name="Execution Confluence Score",
        min_value=-17,
        max_value=7,
    ),
]

WEIGHTS = [
    EvaluationWeight(criterion_id="market_context.dxy", profile_code=PROFILE, weight=0.02),
    EvaluationWeight(criterion_id="market_context.spy", profile_code=PROFILE, weight=0.02),
    EvaluationWeight(criterion_id="market_context.atr", profile_code=PROFILE, weight=0.1),
    EvaluationWeight(criterion_id="market_context.confluence", profile_code=PROFILE, weight=0.15),
]


def test_hand_verified_weighted_average_with_real_ranges_and_weights():
    """
    DXY=0 -> (0-(-4))/(4-(-4))*100 = 50
    SPY=3 (max) -> (3-(-4))/(3-(-4))*100 = 100
    ATR=-1 (min) -> (-1-(-1))/(2-(-1))*100 = 0
    CONFLUENCE=7 (max) -> (7-(-17))/(7-(-17))*100 = 100

    contributions: 50*0.02 + 100*0.02 + 0*0.1 + 100*0.15 = 1 + 2 + 0 + 15 = 18
    weight sum: 0.02+0.02+0.1+0.15 = 0.29
    raw = 18 / 0.29 = 62.0689... -> round_half_up -> 62
    """
    answers = {
        "market_context.dxy": 0,
        "market_context.spy": 3,
        "market_context.atr": -1,
        "market_context.confluence": 7,
    }
    score, breakdown = score_market_context(CRITERIA, WEIGHTS, answers, PROFILE)
    assert score.value == 62
    assert len(breakdown) == 4
    # TRADEOS_DATABASE_DESIGN.md §6.12 provisions market_context_grade
    # (and execution_grade) columns -- unlike the raw Excel, which only
    # visually labels Confidence/Quality with "grade" -- so this sprint
    # follows the canonical schema and derives a grade here too, the same
    # A+/A/B/C/D thresholds as every other unsigned engine. See
    # CHANGELOG.md, Sprint 3.2.
    assert score.grade is not None


def test_market_context_min_and_max_normalize_to_0_and_100():
    answers = {
        "market_context.dxy": -4,
        "market_context.spy": -4,
        "market_context.atr": 2,
        "market_context.confluence": -17,
    }
    _, breakdown = score_market_context(CRITERIA, WEIGHTS, answers, PROFILE)
    by_id = {row.criterion_id: row for row in breakdown}
    assert by_id["market_context.dxy"].normalized_value == 0
    assert by_id["market_context.confluence"].normalized_value == 0
    assert by_id["market_context.atr"].normalized_value == 100


def test_di_04_the_function_signature_has_no_bias_shaped_parameter():
    """Structural enforcement of DI-04: Market Context must never be able
    to receive Bias's score or direction as an input."""
    parameter_names = set(inspect.signature(score_market_context).parameters)
    forbidden_substrings = ("bias", "direction")
    for name in parameter_names:
        lowered = name.lower()
        assert not any(forbidden in lowered for forbidden in forbidden_substrings), (
            f"score_market_context gained a Bias-shaped parameter: '{name}' "
            "(violates Domain Invariant DI-04)"
        )
