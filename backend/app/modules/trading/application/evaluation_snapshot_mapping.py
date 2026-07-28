"""
Shared mapping: an Evaluation `EvaluationResult` (read structurally, never
imported as a type — see `register_trade.py`'s own docstring for why)
into Trading's own `EvaluationSnapshot` domain shape.

Factored out here once `ReevaluateTradeUseCase` (Sprint 4.2) needed
exactly the same construction logic `RegisterTradeUseCase` (Sprint 4.1)
already had inline — reused, not duplicated. Zero behavior change from
Sprint 4.1's own version of this logic.
"""

import uuid
from typing import Any

from app.modules.trading.domain.evaluation_snapshot import (
    EvaluationSnapshot,
    EvaluationSnapshotBreakdown,
)

# The five engines the generic core is instantiated for (PROJECT_AUDIT.md
# §3.2) -- four graded the same way, Bias handled separately (no grade).
GRADED_ENGINES = ("confidence", "quality", "execution", "market_context")


def build_evaluation_snapshot(
    *,
    trade_id: uuid.UUID,
    configuration_version_id: uuid.UUID,
    evaluation_result: Any,
    is_current: bool = True,
) -> EvaluationSnapshot:
    breakdowns: list[EvaluationSnapshotBreakdown] = []
    for engine_type_code in GRADED_ENGINES:
        engine_result = getattr(evaluation_result, engine_type_code)
        breakdowns.extend(_breakdown_rows(engine_type_code, engine_result.breakdown))
    breakdowns.extend(_breakdown_rows("bias", evaluation_result.bias.breakdown))

    return EvaluationSnapshot(
        trade_id=trade_id,
        configuration_version_id=configuration_version_id,
        confidence_score=evaluation_result.confidence.score.value,
        confidence_grade=_grade_value(evaluation_result.confidence.score.grade),
        quality_score=evaluation_result.quality.score.value,
        quality_grade=_grade_value(evaluation_result.quality.score.grade),
        execution_score=evaluation_result.execution.score.value,
        execution_grade=_grade_value(evaluation_result.execution.score.grade),
        market_context_score=evaluation_result.market_context.score.value,
        market_context_grade=_grade_value(evaluation_result.market_context.score.grade),
        bias_score=evaluation_result.bias.score.value,
        breakdowns=breakdowns,
        is_current=is_current,
    )


def _grade_value(grade: Any) -> str | None:
    return grade.value if grade is not None else None


def _breakdown_rows(engine_type_code: str, rows: list[Any]) -> list[EvaluationSnapshotBreakdown]:
    return [
        EvaluationSnapshotBreakdown(
            criterion_id=row.criterion_id,
            engine_type_code=engine_type_code,
            criterion_name_at_time=row.criterion_name,
            raw_value=row.raw_value,
            normalized_value=row.normalized_value,
            weight=row.weight,
            contribution=row.contribution,
        )
        for row in rows
    ]
