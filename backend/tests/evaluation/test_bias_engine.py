"""
Bias engine tests.

The fixtures below are **synthetic, illustrative placeholders only** —
`bias.test_*` ids, never resembling a real Sprint-2.1-style criterion
name (e.g. never `bias.dxy`) — deliberately, to avoid any appearance of
smuggling in unapproved real Bias business data. Their only purpose is to
prove the *mechanism* (signed aggregation via the unmodified generic
core, no grade, DI-05/DI-08) is correct. The real Bias criteria/weights,
derived from the actual Excel, are a separate, explicit proposal pending
your review (see the sprint's own final message) — no seed code exists
for them yet.
"""

import inspect

from app.modules.evaluation.domain.bias_engine import score_bias
from app.modules.evaluation.domain.confidence_engine import score_confidence
from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.modules.evaluation.domain.execution_engine import score_execution
from app.modules.evaluation.domain.market_context_engine import score_market_context
from app.modules.evaluation.domain.quality_engine import score_quality

PROFILE = "day_trading"

# Symmetric, clearly-synthetic signed category map -- illustrative only.
# Deliberately small-magnitude (like the real seeded Bias data's category
# points, roughly -5..+5) rather than already -100..100, so these tests
# also exercise BIAS_SCALE_FACTOR the way real answers will.
SIGNED_MAP = {
    "Strongly Bullish": 5,
    "Bullish": 2,
    "Neutral": 0,
    "Bearish": -2,
    "Strongly Bearish": -5,
}

CRITERIA = [
    EvaluationCriterion(
        id="bias.test_macro_signal",
        name="Test Macro Signal",
        min_value=-5,
        max_value=5,
        category_map=SIGNED_MAP,
    ),
    EvaluationCriterion(
        id="bias.test_trend_signal",
        name="Test Trend Signal",
        min_value=-5,
        max_value=5,
        category_map=SIGNED_MAP,
    ),
]

WEIGHTS = [
    EvaluationWeight(criterion_id="bias.test_macro_signal", profile_code=PROFILE, weight=0.6),
    EvaluationWeight(criterion_id="bias.test_trend_signal", profile_code=PROFILE, weight=0.4),
]


def test_bias_can_produce_a_negative_signed_score():
    """DI-05: Bias is signed -- its score must be able to fall below
    zero, unlike every unsigned engine."""
    answers = {"bias.test_macro_signal": "Strongly Bearish", "bias.test_trend_signal": "Bearish"}
    score, breakdown = score_bias(CRITERIA, WEIGHTS, answers, PROFILE)
    # (-5*0.6 + -2*0.4) / (0.6+0.4) = (-3 + -0.8) / 1.0 = -3.8
    # BIAS_SCALE_FACTOR (real Bias data proposal, decision #5) applies on
    # top: -3.8 * 20 = -76.
    assert score.value == -76
    assert len(breakdown) == 2


def test_bias_can_also_produce_a_positive_score():
    answers = {"bias.test_macro_signal": "Strongly Bullish", "bias.test_trend_signal": "Bullish"}
    score, _ = score_bias(CRITERIA, WEIGHTS, answers, PROFILE)
    # (5*0.6 + 2*0.4) / 1.0 = 3.8, scaled by BIAS_SCALE_FACTOR=20 -> 76
    assert score.value == 76


def test_neutral_inputs_score_exactly_zero():
    answers = {"bias.test_macro_signal": "Neutral", "bias.test_trend_signal": "Neutral"}
    score, _ = score_bias(CRITERIA, WEIGHTS, answers, PROFILE)
    assert score.value == 0


def test_di_05_bias_never_has_a_grade():
    """TRADEOS_DATABASE_DESIGN.md §6.12: no bias_grade column -- "a
    directional score does not map to a quality grade." """
    for answers in (
        {"bias.test_macro_signal": "Strongly Bullish", "bias.test_trend_signal": "Bullish"},
        {"bias.test_macro_signal": "Neutral", "bias.test_trend_signal": "Neutral"},
        {"bias.test_macro_signal": "Strongly Bearish", "bias.test_trend_signal": "Bearish"},
    ):
        score, _ = score_bias(CRITERIA, WEIGHTS, answers, PROFILE)
        assert score.grade is None


def test_di_05_bias_is_the_only_engine_that_never_derives_a_grade():
    """DI-05: "Exactly one Engine (Bias) uses signed normalization; all
    four others use unsigned" -- operationalized as: Bias is the only one
    of the five whose Score always has grade=None; every other engine
    always has a real Grade."""
    bias_score, _ = score_bias(CRITERIA, WEIGHTS, {}, PROFILE)
    assert bias_score.grade is None

    # A minimal, valid answer/criteria/weight set for each unsigned
    # engine, just enough to prove each one *does* derive a grade.
    unsigned_criterion = EvaluationCriterion(
        id="x", name="x", min_value=0, max_value=100, category_map={"Yes": 100, "No": 0}
    )
    unsigned_weight = EvaluationWeight(criterion_id="x", profile_code=PROFILE, weight=1.0)
    answers = {"x": "Yes"}

    for engine in (score_confidence, score_quality, score_execution, score_market_context):
        score, _ = engine([unsigned_criterion], [unsigned_weight], answers, PROFILE)
        assert score.grade is not None, f"{engine.__name__} should always derive a Grade"


def test_di_08_breakdown_is_never_empty_when_weights_are_active_and_answered():
    """Every Score must be explainable -- a populated breakdown, one row
    per contributing criterion."""
    answers = {"bias.test_macro_signal": "Bullish", "bias.test_trend_signal": "Bearish"}
    _, breakdown = score_bias(CRITERIA, WEIGHTS, answers, PROFILE)
    assert len(breakdown) == 2
    ids = {row.criterion_id for row in breakdown}
    assert ids == {"bias.test_macro_signal", "bias.test_trend_signal"}


def test_bias_signature_has_no_dependency_on_any_other_engines_output():
    """Confirms score_bias, like every other engine, is a pure function
    of criteria/weights/answers/profile alone -- no cross-engine
    parameter of any kind."""
    parameter_names = set(inspect.signature(score_bias).parameters)
    assert parameter_names == {"criteria", "weights", "answers", "profile_code"}
