"""
Execution engine tests — real Sprint 2.1 fixtures. Known values verified
directly against `legacy/Trading Journal v2.0 Stable.xlsx`'s real
EXECUTION SCORE column for rows 2 and 3 (extracted alongside Sprint 3.1's
Confidence/Quality known cases).
"""

from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.modules.evaluation.domain.execution_engine import score_execution
from app.shared_kernel.value_objects import Grade

PROFILE = "day_trading"

CRITERIA = [
    EvaluationCriterion(
        id="execution.entry_timing",
        name="Entry Timing",
        min_value=0,
        max_value=100,
        category_map={
            "Perfect": 100,
            "Slightly Early": 70,
            "Slightly Late": 70,
            "Too Early": 30,
            "Too Late": 30,
        },
    ),
    EvaluationCriterion(
        id="execution.stop_placement",
        name="Stop Placement",
        min_value=0,
        max_value=100,
        category_map={"Perfect": 100, "Too Tight": 50, "Too Wide": 50},
    ),
    EvaluationCriterion(
        id="execution.tp_execution",
        name="TP Execution",
        min_value=0,
        max_value=100,
        category_map={"Perfect": 100, "Exited Early": 60, "Exited Late": 60},
    ),
    EvaluationCriterion(
        id="execution.management",
        name="Management",
        min_value=0,
        max_value=100,
        category_map={"Excellent": 100, "Good": 80, "Average": 50, "Poor": 20},
    ),
]

WEIGHTS = [
    EvaluationWeight(criterion_id="execution.entry_timing", profile_code=PROFILE, weight=0.25),
    EvaluationWeight(criterion_id="execution.stop_placement", profile_code=PROFILE, weight=0.25),
    EvaluationWeight(criterion_id="execution.tp_execution", profile_code=PROFILE, weight=0.25),
    EvaluationWeight(criterion_id="execution.management", profile_code=PROFILE, weight=0.25),
]


def test_known_case_rows_2_and_3_both_score_58():
    """Both real rows share the same real EXECUTION SCORE (58, Grade D)
    despite differing on tp_execution (Exited Late vs Exited Early), since
    both map to the same normalized value (60)."""
    for tp_value in ("Exited Late", "Exited Early"):
        answers = {
            "execution.entry_timing": "Perfect",
            "execution.stop_placement": "Too Tight",
            "execution.tp_execution": tp_value,
            "execution.management": "Poor",
        }
        score, breakdown = score_execution(CRITERIA, WEIGHTS, answers, PROFILE)
        assert score.value == 58
        assert score.grade == Grade.D
        assert len(breakdown) == 4


def test_perfect_execution_scores_100_grade_a_plus():
    answers = {
        "execution.entry_timing": "Perfect",
        "execution.stop_placement": "Perfect",
        "execution.tp_execution": "Perfect",
        "execution.management": "Excellent",
    }
    score, _ = score_execution(CRITERIA, WEIGHTS, answers, PROFILE)
    assert score.value == 100
    assert score.grade == Grade.A_PLUS
