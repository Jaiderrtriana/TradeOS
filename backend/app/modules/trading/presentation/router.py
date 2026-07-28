"""
Trading presentation: `POST /trades` (Sprint 4.1); `PATCH /trades/{id}`,
`POST /trades/{id}/close`, `POST /trades/{id}/reevaluate`,
`DELETE /trades/{id}` (Sprint 4.2); `POST /trades/{id}/mistakes`
(Sprint 4.3) — `TRADEOS_API_SPECIFICATION.md` §6.4. `GET /trades`,
`GET /trades/{id}`, `GET /trades/{id}/mistakes`, and
`DELETE /trades/{id}/mistakes/{catalogEntryId}` remain out of scope,
confirmed for Sprint 4.3 (deferred to whichever sprint first names them
explicitly — same "Master Plan Objectives, not the API surface, define
sprint scope" reasoning already applied in Sprint 4.2).

`Idempotency-Key` (optional header, §3.6) is handled here, at the router,
via the generic `app/platform/idempotency.py` helper — a cross-cutting
concern, not Trading-specific — and applies only to `POST /trades`
(§3.6: "Every `POST` that creates a resource" — `PATCH`/`DELETE` are
idempotent by HTTP method semantics already, `close`/`reevaluate` are
explicitly excluded, and `mistakes` needs no such mechanism either: its
own composite primary key already makes a duplicate request safe,
without a network-retry "double-logging" risk POST /trades has for a
brand-new aggregate root).
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
from app.modules.trading.application.amend_trade import AmendTradeUseCase
from app.modules.trading.application.close_trade import CloseTradeUseCase
from app.modules.trading.application.delete_trade import DeleteTradeUseCase
from app.modules.trading.application.reevaluate_trade import ReevaluateTradeUseCase
from app.modules.trading.application.register_trade import RegisterTradeUseCase
from app.modules.trading.application.tag_mistake import TagMistakeUseCase
from app.modules.trading.domain.evaluation_snapshot import EvaluationSnapshot
from app.modules.trading.domain.trade import Trade
from app.modules.trading.infrastructure.repository import (
    ChecklistSnapshotRepository,
    EvaluationSnapshotRepository,
    TradeMistakeRepository,
    TradeRepository,
)
from app.modules.trading.presentation.schemas import (
    AmendTradeRequest,
    BiasEngineResultResponse,
    CloseTradeRequest,
    CriterionBreakdownRowResponse,
    EvaluationSnapshotResponse,
    GradedEngineResultResponse,
    ReevaluateTradeRequest,
    RegisterTradeRequest,
    TagMistakeRequest,
    TradeMistakeResponse,
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
    response = _trade_response(result.trade, result.evaluation)

    if claim is not None:
        await store_idempotent_response(
            session, claim, status=status.HTTP_201_CREATED, body=response.model_dump(mode="json")
        )

    await session.commit()
    return response


@router.patch("/{trade_id}", response_model=TradeResponse)
async def amend_trade(
    trade_id: UUID,
    payload: AmendTradeRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> TradeResponse:
    use_case = AmendTradeUseCase(TradeRepository(session), dispatcher, session)
    trade = await use_case.execute(trade_id, user_id, payload.model_dump(exclude_unset=True))
    evaluation = await _require_current_evaluation(session, trade_id)
    await session.commit()
    return _trade_response(trade, evaluation)


@router.post("/{trade_id}/close", response_model=TradeResponse)
async def close_trade(
    trade_id: UUID,
    payload: CloseTradeRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> TradeResponse:
    use_case = CloseTradeUseCase(TradeRepository(session), dispatcher, session)
    trade = await use_case.execute(
        trade_id,
        user_id,
        result=payload.result,
        exit_price=payload.exit_price,
        mfe_price=payload.mfe_price,
        mae_price=payload.mae_price,
    )
    evaluation = await _require_current_evaluation(session, trade_id)
    await session.commit()
    return _trade_response(trade, evaluation)


@router.post("/{trade_id}/reevaluate", response_model=EvaluationSnapshotResponse)
async def reevaluate_trade(
    trade_id: UUID,
    payload: ReevaluateTradeRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> EvaluationSnapshotResponse:
    use_case = ReevaluateTradeUseCase(
        TradeRepository(session),
        ChecklistSnapshotRepository(session),
        EvaluationSnapshotRepository(session),
        build_get_configuration_version_use_case(session),
        build_preview_evaluation_use_case(session),
        dispatcher,
        session,
    )
    snapshot = await use_case.execute(
        trade_id,
        user_id,
        scoring_profile=payload.scoring_profile,
        configuration_version_id=payload.configuration_version_id,
    )
    await session.commit()
    return _evaluation_response(snapshot)


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(
    trade_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    use_case = DeleteTradeUseCase(TradeRepository(session))
    await use_case.execute(trade_id, user_id)
    await session.commit()


@router.post(
    "/{trade_id}/mistakes",
    response_model=TradeMistakeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def tag_mistake(
    trade_id: UUID,
    payload: TagMistakeRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> TradeMistakeResponse:
    use_case = TagMistakeUseCase(
        TradeRepository(session),
        TradeMistakeRepository(session),
        build_get_catalog_entry_use_case(session),
        dispatcher,
        session,
    )
    trade_mistake = await use_case.execute(trade_id, user_id, payload.catalog_entry_id)
    await session.commit()
    return TradeMistakeResponse(
        trade_id=trade_mistake.trade_id,
        catalog_entry_id=trade_mistake.catalog_entry_id,
        created_at=trade_mistake.created_at,
    )


async def _require_current_evaluation(session: AsyncSession, trade_id: UUID) -> EvaluationSnapshot:
    """Every Trade owns exactly one current `EvaluationSnapshot`, maintained
    since `RegisterTrade` -- a `None` here would be a genuine data-integrity
    bug elsewhere, not a request-shape concern, so it fails loudly rather
    than being folded into the request-facing error envelope."""
    evaluation = await EvaluationSnapshotRepository(session).get_current_by_trade_id(trade_id)
    if evaluation is None:
        raise RuntimeError(f"Trade '{trade_id}' has no current EvaluationSnapshot.")
    return evaluation


def _trade_response(trade: Trade, evaluation: EvaluationSnapshot) -> TradeResponse:
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
        evaluation=_evaluation_response(evaluation),
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
