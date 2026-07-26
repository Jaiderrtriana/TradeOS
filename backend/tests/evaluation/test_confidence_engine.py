"""
Confidence engine tests — TRADEOS_IMPLEMENTATION_MASTER_PLAN.md Sprint
3.1's own "known test cases" Deliverable, plus INV-WEIGHT-01.

Criteria/weights are the exact real values Sprint 2.1 seeded
(scripts/seed_configuration.py) — reproduced here as in-memory fixtures,
never read from a database (this sprint's approved "zero infrastructure
dependencies" scope). The two known cases are rows 2 and 3 of
`legacy/Trading Journal v2.0 Stable.xlsx`'s Trades sheet, with Excel's own
already-computed TRADE CONFIDENCE values as the expected result.
"""

from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.modules.evaluation.domain.confidence_engine import score_confidence
from app.shared_kernel.value_objects import Grade

PROFILE = "day_trading"

CRITERIA = [
    EvaluationCriterion(
        id="confidence.bias_index_at_entry", name="Bias Index @ Entry", min_value=0, max_value=100
    ),
    EvaluationCriterion(
        id="confidence.htf_alignment",
        name="HTF Alignment",
        min_value=0,
        max_value=100,
        category_map={
            "Full Alignment": 100,
            "Moderate Alignment": 70,
            "Partial Conflict": 40,
            "Full Conflict": 0,
        },
    ),
    EvaluationCriterion(
        id="confidence.ltf_confirmation",
        name="LTF Confirmation",
        min_value=0,
        max_value=100,
        category_map={"Yes": 100, "Partial": 50, "No": 0},
    ),
    EvaluationCriterion(
        id="confidence.emotional_state",
        name="Emotional State",
        min_value=0,
        max_value=100,
        category_map={"Calm": 100, "Slightly Emotional": 70, "Emotional": 30, "Revenge Trading": 0},
    ),
]

WEIGHTS = [
    EvaluationWeight(
        criterion_id="confidence.bias_index_at_entry", profile_code=PROFILE, weight=0.5
    ),
    EvaluationWeight(criterion_id="confidence.htf_alignment", profile_code=PROFILE, weight=0.2),
    EvaluationWeight(criterion_id="confidence.ltf_confirmation", profile_code=PROFILE, weight=0.15),
    EvaluationWeight(criterion_id="confidence.emotional_state", profile_code=PROFILE, weight=0.15),
]


def test_known_case_row_2_the_round_half_up_case():
    """Bias=21 (signed positive here, but ABS() applies regardless),
    HTF=Partial Conflict, LTF=Yes, Emotional=Calm. Raw weighted score is
    exactly 48.5 -- Excel's real TRADE CONFIDENCE for this row is 49."""
    answers = {
        "confidence.bias_index_at_entry": 21.0,
        "confidence.htf_alignment": "Partial Conflict",
        "confidence.ltf_confirmation": "Yes",
        "confidence.emotional_state": "Calm",
    }
    score, breakdown = score_confidence(CRITERIA, WEIGHTS, answers, PROFILE)
    assert score.value == 49
    assert score.grade == Grade.D
    assert len(breakdown) == 4


def test_known_case_row_3():
    """Bias=3, HTF=Partial Conflict, LTF=Yes, Emotional=Calm. Excel's real
    TRADE CONFIDENCE for this row is 40."""
    answers = {
        "confidence.bias_index_at_entry": 3.0,
        "confidence.htf_alignment": "Partial Conflict",
        "confidence.ltf_confirmation": "Yes",
        "confidence.emotional_state": "Calm",
    }
    score, _ = score_confidence(CRITERIA, WEIGHTS, answers, PROFILE)
    assert score.value == 40
    assert score.grade == Grade.D


def test_bias_index_is_scored_on_its_absolute_value():
    """A negative Bias Index must score identically to its positive
    counterpart -- ROUND(ABS(AF2)*W_CONF_BIAS + ..., 0) in the real Excel
    formula."""
    answers = {
        "confidence.bias_index_at_entry": -21.0,
        "confidence.htf_alignment": "Partial Conflict",
        "confidence.ltf_confirmation": "Yes",
        "confidence.emotional_state": "Calm",
    }
    score, _ = score_confidence(CRITERIA, WEIGHTS, answers, PROFILE)
    assert score.value == 49


def test_inv_weight_01_deactivated_weight_is_excluded_from_denominator():
    """INV-WEIGHT-01: aggregation divides by the sum of *active* weights
    only. Deactivating LTF Confirmation's weight must remove it from both
    the numerator and the denominator, not merely zero its contribution."""
    weights_with_ltf_inactive = [
        EvaluationWeight(
            criterion_id="confidence.bias_index_at_entry", profile_code=PROFILE, weight=0.5
        ),
        EvaluationWeight(criterion_id="confidence.htf_alignment", profile_code=PROFILE, weight=0.2),
        EvaluationWeight(
            criterion_id="confidence.ltf_confirmation",
            profile_code=PROFILE,
            weight=0.15,
            is_active=False,
        ),
        EvaluationWeight(
            criterion_id="confidence.emotional_state", profile_code=PROFILE, weight=0.15
        ),
    ]
    answers = {
        "confidence.bias_index_at_entry": 21.0,
        "confidence.htf_alignment": "Partial Conflict",
        "confidence.ltf_confirmation": "Yes",  # answered, but its weight is inactive
        "confidence.emotional_state": "Calm",
    }
    score, breakdown = score_confidence(CRITERIA, weights_with_ltf_inactive, answers, PROFILE)

    # (21*0.5 + 40*0.2 + 100*0.15) / (0.5 + 0.2 + 0.15) = 33.5 / 0.85 = 39.41... -> 39
    assert score.value == 39
    assert len(breakdown) == 3
    assert all(row.criterion_id != "confidence.ltf_confirmation" for row in breakdown)


def test_missing_answer_is_handled_gracefully_not_an_error():
    """TRADEOS_BACKEND_BLUEPRINT.md §4.1: "missing checklist answers
    handled gracefully by the Evaluation Engine itself." """
    answers = {
        "confidence.bias_index_at_entry": 21.0,
        "confidence.htf_alignment": "Partial Conflict",
        # ltf_confirmation and emotional_state intentionally omitted
    }
    score, breakdown = score_confidence(CRITERIA, WEIGHTS, answers, PROFILE)
    assert len(breakdown) == 2
    assert score.value >= 0


def test_a_different_profile_with_no_matching_weights_yields_zero():
    score, breakdown = score_confidence(
        CRITERIA, WEIGHTS, {"confidence.bias_index_at_entry": 21.0}, "swing_trading"
    )
    assert score.value == 0
    assert breakdown == []
