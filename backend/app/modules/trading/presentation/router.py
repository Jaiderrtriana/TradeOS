"""
Trading presentation: `POST /trades` (TRADEOS_API_SPECIFICATION.md §6.4).
The only Trading endpoint in scope for Sprint 4.1 — `GET /trades`,
`GET /trades/{id}`, `PATCH`, `/close`, `/reevaluate`, `DELETE`, and the
Mistakes sub-resource all belong to later sprints (4.2/4.3).

`Idempotency-Key` (optional header, §3.6) is handled here, at the router,
via the generic `app/platform/idempotency.py` helper — a cross-cutting
concern, not Trading-specific — wrapping exactly the one write this
endpoint performs.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.get_catalog_entry import (
    build_get_catalog_entry_use_case,
)
from app.modules.configuration.application.get_configuration_version import (
    build_get_configuration_version_use_case,
)
from app.modules.evaluation.application.preview_evaluation import (
    build_preview_evaluation_use_case,
)
from app.modules.trading.application.register_trade import (
    RegisterTradeResult,
    RegisterTradeUseCase,
)
from app.modules.trading.domain.evaluation_snapshot import EvaluationSnapshot
from app.modules.trading.infrastructure.repository import (
    ChecklistSnapshotRepository,
    EvaluationSnapshotRepository,
    TradeRepository,
)
from app.modules.trading.presentation.schemas import (
    BiasEngineResultResponse,
    CriterionBreakdownRowResponse,
    EvaluationSnapshotResponse,
    GradedEngineResultResponse,
    RegisterTradeRequest,
    TradeResponse,
)
from app.platform.db.session import get_db_session
from app.platform.events.dispatcher import dispatcher
from app.platform.idempotency import (
    Claim,
    StoredResponse,
    claim_idempotency_key,
    store_idempotent_response,
)
from app.platform.security.dependencies import get_current_user_id

router = APIRouter(prefix="/trades", tags=["trading"])


@router.post("", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
async def register_trade(
    payload: RegisterTradeRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> TradeResponse | JSONResponse:
    claim: Claim | None = None
    if idempotency_key is not None:
        claimed = await claim_idempotency_key(
            session, user_id=user_id, idempotency_key=idempotency_key, endpoint="POST /trades"
        )
        if isinstance(claimed, StoredResponse):
            return JSONResponse(status_code=claimed.status, content=claimed.body)
        claim = claimed

    use_case = RegisterTradeUseCase(
        TradeRepository(session),
        ChecklistSnapshotRepository(session),
        EvaluationSnapshotRepository(session),
        build_get_catalog_entry_use_case(session),
        build_get_configuration_version_use_case(session),
        build_preview_evaluation_use_case(session),
        dispatcher,
        session,
    )
    result = await use_case.execute(
        user_id=user_id,
        market=payload.market,
        direction=payload.direction,
        entry_price=payload.entry_price,
        stop_loss=payload.stop_loss,
        scoring_profile=payload.scoring_profile,
        exit_price=payload.exit_price,
        size=payload.size,
        leverage=payload.leverage,
        result=payload.result,
        strategy_id=payload.strategy_id,
        setup_id=payload.setup_id,
        session_id=payload.session_id,
        entry_trigger_id=payload.entry_trigger_id,
        notes=payload.notes,
        mfe_price=payload.mfe_price,
        mae_price=payload.mae_price,
        checklist_answers=payload.checklist_answers,
    )
    response = _trade_response(result)

    if claim is not None:
        await store_idempotent_response(
            session, claim, status=status.HTTP_201_CREATED, body=response.model_dump(mode="json")
        )

    await session.commit()
    return response


def _trade_response(result: RegisterTradeResult) -> TradeResponse:
    trade = result.trade
    return TradeResponse(
        id=trade.id,
        market=trade.market,
        direction=trade.direction,
        entry_price=trade.entry_price,
        stop_loss=trade.stop_loss,
        exit_price=trade.exit_price,
        size=trade.size,
        leverage=trade.leverage,
        result=trade.result,
        realized_pnl=trade.realized_pnl,
        mfe_price=trade.mfe_price,
        mae_price=trade.mae_price,
        notes=trade.notes,
        strategy_id=trade.strategy_id,
        setup_id=trade.setup_id,
        session_id=trade.session_id,
        entry_trigger_id=trade.entry_trigger_id,
        entered_at=trade.entered_at,
        closed_at=trade.closed_at,
        created_at=trade.created_at,
        updated_at=trade.updated_at,
        r_multiple=trade.r_multiple,
        mfe_r=trade.mfe_r,
        mae_r=trade.mae_r,
        captured_pct=trade.captured_pct,
        potential_left_r=trade.potential_left_r,
        evaluation=_evaluation_response(result.evaluation),
    )


def _evaluation_response(snapshot: EvaluationSnapshot) -> EvaluationSnapshotResponse:
    breakdown_by_engine: dict[str, list[CriterionBreakdownRowResponse]] = {
        "confidence": [],
        "quality": [],
        "execution": [],
        "market_context": [],
        "bias": [],
    }
    for row in snapshot.breakdowns:
        breakdown_by_engine[row.engine_type_code].append(
            CriterionBreakdownRowResponse(
                criterion_id=row.criterion_id,
                criterion_name=row.criterion_name_at_time,
                raw_value=row.raw_value,
                normalized_value=row.normalized_value,
                weight=row.weight,
                contribution=row.contribution,
            )
        )
    return EvaluationSnapshotResponse(
        confidence=GradedEngineResultResponse(
            score=snapshot.confidence_score,
            grade=snapshot.confidence_grade,
            breakdown=breakdown_by_engine["confidence"],
        ),
        quality=GradedEngineResultResponse(
            score=snapshot.quality_score,
            grade=snapshot.quality_grade,
            breakdown=breakdown_by_engine["quality"],
        ),
        execution=GradedEngineResultResponse(
            score=snapshot.execution_score,
            grade=snapshot.execution_grade,
            breakdown=breakdown_by_engine["execution"],
        ),
        market_context=GradedEngineResultResponse(
            score=snapshot.market_context_score,
            grade=snapshot.market_context_grade,
            breakdown=breakdown_by_engine["market_context"],
        ),
        bias=BiasEngineResultResponse(
            score=snapshot.bias_score,
            breakdown=breakdown_by_engine["bias"],
        ),
    )
