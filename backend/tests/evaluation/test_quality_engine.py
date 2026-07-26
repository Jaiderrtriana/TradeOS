"""
Quality engine tests — net-new this sprint (no reference implementation
existed to port). Same real Sprint 2.1 fixtures and known Excel rows as
Confidence. Domain Invariant DI-03 / INV-QUALITY-01 (Quality independent
of P&L) is asserted both structurally (the function cannot even accept a
financial-outcome parameter) and by the engine's own type contract.
"""

import inspect

from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.modules.evaluation.domain.quality_engine import score_quality
from app.shared_kernel.value_objects import Grade

PROFILE = "day_trading"

CRITERIA = [
    EvaluationCriterion(
        id="quality.followed_plan",
        name="Followed Plan",
        min_value=0,
        max_value=100,
        category_map={"Yes": 100, "No": 0},
    ),
    EvaluationCriterion(
        id="quality.valid_setup",
        name="Valid Setup",
        min_value=0,
        max_value=100,
        category_map={"Yes": 100, "No": 0},
    ),
    EvaluationCriterion(
        id="quality.entered_at_planned_level",
        name="Entered at Planned Level",
        min_value=0,
        max_value=100,
        category_map={"Yes": 100, "No": 0},
    ),
    EvaluationCriterion(
        id="quality.respected_stop",
        name="Respected Stop",
        min_value=0,
        max_value=100,
        category_map={"Yes": 100, "No": 0},
    ),
    EvaluationCriterion(
        id="quality.respected_tp",
        name="Respected TP",
        min_value=0,
        max_value=100,
        category_map={"Yes": 100, "N/A": 100, "Exited Early": 60, "Exited Late": 40, "No": 0},
    ),
    EvaluationCriterion(
        id="quality.respected_risk_mgmt",
        name="Respected Risk Mgmt",
        min_value=0,
        max_value=100,
        category_map={"Yes": 100, "No": 0},
    ),
]

WEIGHTS = [
    EvaluationWeight(criterion_id="quality.followed_plan", profile_code=PROFILE, weight=0.2),
    EvaluationWeight(criterion_id="quality.valid_setup", profile_code=PROFILE, weight=0.15),
    EvaluationWeight(
        criterion_id="quality.entered_at_planned_level", profile_code=PROFILE, weight=0.15
    ),
    EvaluationWeight(criterion_id="quality.respected_stop", profile_code=PROFILE, weight=0.2),
    EvaluationWeight(criterion_id="quality.respected_tp", profile_code=PROFILE, weight=0.15),
    EvaluationWeight(criterion_id="quality.respected_risk_mgmt", profile_code=PROFILE, weight=0.15),
]


def test_known_case_row_2_a_losing_trade_with_a_high_quality_score():
    """TRADEOS_DOMAIN_MODEL.md BR-003 / DI-03, made concrete: this trade
    lost money (result=SL, pnl=-1.05 in the real Excel row) yet its real
    TRADE QUALITY is 85 (Grade B) -- a losing trade can still be a
    high-quality one, because the score never looks at the outcome."""
    answers = {
        "quality.followed_plan": "Yes",
        "quality.valid_setup": "Yes",
        "quality.entered_at_planned_level": "Yes",
        "quality.respected_stop": "Yes",
        "quality.respected_tp": "Yes",
        "quality.respected_risk_mgmt": "No",
    }
    score, breakdown = score_quality(CRITERIA, WEIGHTS, answers, PROFILE)
    assert score.value == 85
    assert score.grade == Grade.B
    assert len(breakdown) == 6


def test_known_case_row_3():
    """Excel's real TRADE QUALITY for this row is 65 (Grade D)."""
    answers = {
        "quality.followed_plan": "Yes",
        "quality.valid_setup": "Yes",
        "quality.entered_at_planned_level": "Yes",
        "quality.respected_stop": "No",
        "quality.respected_tp": "Yes",
        "quality.respected_risk_mgmt": "No",
    }
    score, _ = score_quality(CRITERIA, WEIGHTS, answers, PROFILE)
    assert score.value == 65
    assert score.grade == Grade.D


def test_di_03_the_function_signature_has_no_pnl_or_result_parameter():
    """Structural enforcement of DI-03: it must be impossible to pass a
    financial outcome into this engine at all, not merely "not done
    today." Fails if anyone ever adds a `pnl`/`result`/`outcome`-shaped
    parameter to score_quality."""
    parameter_names = set(inspect.signature(score_quality).parameters)
    forbidden_substrings = ("pnl", "result", "outcome", "profit", "loss", "p_and_l")
    for name in parameter_names:
        lowered = name.lower()
        assert not any(forbidden in lowered for forbidden in forbidden_substrings), (
            f"score_quality gained a financial-outcome-shaped parameter: '{name}' "
            "(violates Domain Invariant DI-03)"
        )


def test_respected_tp_na_scores_identically_to_yes():
    """TP_RESPECTED_SCORES: "N/A" maps to 100, same as "Yes" -- a trade
    where TP was never reached (e.g. stopped out) is not penalized for it."""
    answers_with_yes = {
        "quality.followed_plan": "Yes",
        "quality.valid_setup": "Yes",
        "quality.entered_at_planned_level": "Yes",
        "quality.respected_stop": "Yes",
        "quality.respected_tp": "Yes",
        "quality.respected_risk_mgmt": "Yes",
    }
    answers_with_na = {**answers_with_yes, "quality.respected_tp": "N/A"}

    score_yes, _ = score_quality(CRITERIA, WEIGHTS, answers_with_yes, PROFILE)
    score_na, _ = score_quality(CRITERIA, WEIGHTS, answers_with_na, PROFILE)
    assert score_yes.value == score_na.value == 100
    assert score_yes.grade == score_na.grade == Grade.A_PLUS


def test_inv_weight_01_deactivated_weight_is_excluded_from_denominator():
    weights_with_risk_mgmt_inactive = [
        EvaluationWeight(criterion_id="quality.followed_plan", profile_code=PROFILE, weight=0.2),
        EvaluationWeight(criterion_id="quality.valid_setup", profile_code=PROFILE, weight=0.15),
        EvaluationWeight(
            criterion_id="quality.entered_at_planned_level", profile_code=PROFILE, weight=0.15
        ),
        EvaluationWeight(criterion_id="quality.respected_stop", profile_code=PROFILE, weight=0.2),
        EvaluationWeight(criterion_id="quality.respected_tp", profile_code=PROFILE, weight=0.15),
        EvaluationWeight(
            criterion_id="quality.respected_risk_mgmt",
            profile_code=PROFILE,
            weight=0.15,
            is_active=False,
        ),
    ]
    answers = {
        "quality.followed_plan": "Yes",
        "quality.valid_setup": "Yes",
        "quality.entered_at_planned_level": "Yes",
        "quality.respected_stop": "Yes",
        "quality.respected_tp": "Yes",
        "quality.respected_risk_mgmt": "No",  # answered, but weight inactive
    }
    score, breakdown = score_quality(CRITERIA, weights_with_risk_mgmt_inactive, answers, PROFILE)
    # All 5 remaining active criteria answered "Yes" -> 100 regardless of
    # their individual weights, since every one contributes its full
    # normalized value.
    assert score.value == 100
    assert len(breakdown) == 5
    assert all(row.criterion_id != "quality.respected_risk_mgmt" for row in breakdown)
