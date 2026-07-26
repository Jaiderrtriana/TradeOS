"""
Orchestrator tests — Domain Invariant DI-08 (every Score must be
explainable) verified across all five engines at once, plus confirmation
that all five run independently off one shared `answers` map without
interfering with each other.
"""

from app.modules.evaluation.domain.evaluation_engine import evaluate
from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_result import EngineInput
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight

PROFILE = "day_trading"


def _single_criterion_input(criterion_id: str, category_map: dict) -> EngineInput:
    criterion = EvaluationCriterion(
        id=criterion_id, name=criterion_id, min_value=0, max_value=100, category_map=category_map
    )
    weight = EvaluationWeight(criterion_id=criterion_id, profile_code=PROFILE, weight=1.0)
    return EngineInput(criteria=[criterion], weights=[weight])


def test_evaluate_returns_all_five_engines_with_complete_breakdowns():
    answers = {
        "confidence.x": "Yes",
        "quality.x": "Yes",
        "execution.x": "Yes",
        "market_context.x": "Yes",
        "bias.x": "Bullish",
    }
    result = evaluate(
        confidence=_single_criterion_input("confidence.x", {"Yes": 100, "No": 0}),
        quality=_single_criterion_input("quality.x", {"Yes": 100, "No": 0}),
        execution=_single_criterion_input("execution.x", {"Yes": 100, "No": 0}),
        market_context=_single_criterion_input("market_context.x", {"Yes": 100, "No": 0}),
        bias=_single_criterion_input("bias.x", {"Bullish": 50, "Bearish": -50}),
        answers=answers,
        profile_code=PROFILE,
    )

    assert result.confidence.score.value == 100
    assert result.quality.score.value == 100
    assert result.execution.score.value == 100
    assert result.market_context.score.value == 100
    assert result.bias.score.value == 50

    # DI-08: every engine's Score must carry a non-empty breakdown.
    for engine_result in (
        result.confidence,
        result.quality,
        result.execution,
        result.market_context,
        result.bias,
    ):
        assert len(engine_result.breakdown) == 1

    # DI-05: only Bias is gradeless.
    assert result.confidence.score.grade is not None
    assert result.quality.score.grade is not None
    assert result.execution.score.grade is not None
    assert result.market_context.score.grade is not None
    assert result.bias.score.grade is None


def test_engines_do_not_interfere_with_each_others_answers():
    """Each engine only ever reads the keys it has an active weight for
    -- irrelevant answer keys belonging to other engines are silently
    ignored, never mixed in."""
    shared_answers = {
        "confidence.x": "No",
        "quality.x": "Yes",
        "execution.x": "No",
        "market_context.x": "Yes",
        "bias.x": "Bearish",
    }
    result = evaluate(
        confidence=_single_criterion_input("confidence.x", {"Yes": 100, "No": 0}),
        quality=_single_criterion_input("quality.x", {"Yes": 100, "No": 0}),
        execution=_single_criterion_input("execution.x", {"Yes": 100, "No": 0}),
        market_context=_single_criterion_input("market_context.x", {"Yes": 100, "No": 0}),
        bias=_single_criterion_input("bias.x", {"Bullish": 50, "Bearish": -50}),
        answers=shared_answers,
        profile_code=PROFILE,
    )
    assert result.confidence.score.value == 0
    assert result.quality.score.value == 100
    assert result.execution.score.value == 0
    assert result.market_context.score.value == 100
    assert result.bias.score.value == -50
