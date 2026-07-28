"""
Evaluation presentation: `POST /evaluation/preview`
(TRADEOS_API_SPECIFICATION.md §6.5). The only Evaluation endpoint in
scope for Sprint 3.2 — `GET /trades/{id}/evaluation` and its `/history`
variant belong to the Trades module (Phase 4, not yet built).
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.evaluation.application.preview_evaluation import (
    build_preview_evaluation_use_case,
)
from app.modules.evaluation.domain.criterion_breakdown_row import CriterionBreakdownRow
from app.modules.evaluation.domain.evaluation_result import EngineResult, EvaluationResult
from app.modules.evaluation.presentation.schemas import (
    BiasEngineResultResponse,
    CriterionBreakdownRowResponse,
    EvaluationSnapshotResponse,
    GradedEngineResultResponse,
    PreviewEvaluationRequest,
)
from app.platform.db.session import get_db_session
from app.platform.security.dependencies import get_current_user_id

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/preview", response_model=EvaluationSnapshotResponse)
async def preview_evaluation(
    payload: PreviewEvaluationRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> EvaluationSnapshotResponse:
    use_case = build_preview_evaluation_use_case(session)
    result = await use_case.execute(
        checklist_answers=payload.checklist_answers,
        scoring_profile=payload.scoring_profile,
        configuration_version_id=payload.configuration_version_id,
    )
    return _snapshot_response(result)


def _breakdown_response(
    breakdown: list[CriterionBreakdownRow],
) -> list[CriterionBreakdownRowResponse]:
    return [
        CriterionBreakdownRowResponse(
            criterion_id=row.criterion_id,
            criterion_name=row.criterion_name,
            raw_value=row.raw_value,
            normalized_value=row.normalized_value,
            weight=row.weight,
            contribution=row.contribution,
        )
        for row in breakdown
    ]


def _graded_response(engine_result: EngineResult) -> GradedEngineResultResponse:
    return GradedEngineResultResponse(
        score=engine_result.score.value,
        grade=engine_result.score.grade.value if engine_result.score.grade else None,
        breakdown=_breakdown_response(engine_result.breakdown),
    )


def _snapshot_response(result: EvaluationResult) -> EvaluationSnapshotResponse:
    return EvaluationSnapshotResponse(
        confidence=_graded_response(result.confidence),
        quality=_graded_response(result.quality),
        execution=_graded_response(result.execution),
        market_context=_graded_response(result.market_context),
        bias=BiasEngineResultResponse(
            score=result.bias.score.value,
            breakdown=_breakdown_response(result.bias.breakdown),
        ),
    )
