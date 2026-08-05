"""
OpenTradeUseCase — `TRADEOS_API_SPECIFICATION.md` §6.4/§11.1.1,
`POST /trades/{id}/open` (new in v2.0, Trade Entry redesign, Domain Model
KDD-07).

Business Flow (literal order from §11.1.1): load the Trade, `409`
Conflict if `status != planned` (INV-TRADE-04 — a `Trade` can only ever
transition `Planned -> Open`, never `Open -> Open` again and never
directly `Planned -> Closed`) -> apply `entry_price`/`entered_at`/
`stop_loss`/`take_profit` -> re-validate INV-TRADE-01/02 via the same
free functions every other write path uses -> run Evaluation for the
first time, the identical synchronous flow `RegisterTradeUseCase` already
performs when a Trade is created directly as `Open` (never duplicated —
mirrors that Use Case's own Evaluation branch) -> persist Trade +
ChecklistSnapshot + EvaluationSnapshot (+ breakdown rows) in one
transaction -> publish `TradeOpened`, then `TradeEvaluated`.
"""

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.get_configuration_version import (
    GetConfigurationVersionUseCase,
)
from app.modules.evaluation.application.preview_evaluation import PreviewEvaluationUseCase
from app.modules.trading.application.evaluation_snapshot_mapping import build_evaluation_snapshot
from app.modules.trading.domain.checklist_snapshot import ChecklistSnapshot
from app.modules.trading.domain.evaluation_snapshot import EvaluationSnapshot
from app.modules.trading.domain.trade import (
    OPEN,
    PLANNED,
    Trade,
    validate_status_fields,
    validate_stop_placement,
)
from app.modules.trading.infrastructure.repository import (
    ChecklistSnapshotRepository,
    EvaluationSnapshotRepository,
    TradeRepository,
)
from app.platform.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher


class OpenTradeResult:
    def __init__(self, trade: Trade, evaluation: EvaluationSnapshot) -> None:
        self.trade = trade
        self.evaluation = evaluation


class OpenTradeUseCase:
    def __init__(
        self,
        trade_repository: TradeRepository,
        checklist_snapshot_repository: ChecklistSnapshotRepository,
        evaluation_snapshot_repository: EvaluationSnapshotRepository,
        get_configuration_version_use_case: GetConfigurationVersionUseCase,
        preview_evaluation_use_case: PreviewEvaluationUseCase,
        dispatcher: EventDispatcher,
        session: AsyncSession,
    ) -> None:
        self._trades = trade_repository
        self._checklist_snapshots = checklist_snapshot_repository
        self._evaluation_snapshots = evaluation_snapshot_repository
        self._get_configuration_version = get_configuration_version_use_case
        self._preview_evaluation = preview_evaluation_use_case
        self._dispatcher = dispatcher
        self._session = session

    async def execute(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        entry_price: float,
        entered_at: datetime,
        scoring_profile: str,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        checklist_answers: dict[str, str | float] | None = None,
    ) -> OpenTradeResult:
        # SELECT ... FOR UPDATE: same reasoning as ReevaluateTradeUseCase's
        # own row lock -- serializes a concurrent double-`open` against
        # the same Trade.
        trade = await self._trades.get_by_id_for_update(trade_id)
        if trade is None or trade.user_id != user_id or trade.deleted_at is not None:
            raise NotFoundError(f"No trade with id '{trade_id}'.")
        if trade.status != PLANNED:
            raise ConflictError("This trade is not planned.")

        trade.status = OPEN
        trade.entry_price = entry_price
        trade.entered_at = entered_at
        trade.stop_loss = stop_loss
        trade.take_profit = take_profit

        validate_stop_placement(trade.direction, trade.entry_price, trade.stop_loss)
        validate_status_fields(
            trade.status,
            trade.entry_price,
            trade.entered_at,
            trade.exit_price,
            trade.closed_at,
            trade.result,
        )

        answers = checklist_answers or {}

        configuration_version = await self._get_configuration_version.execute()
        if configuration_version is None:
            raise UnprocessableEntityError(
                "No configuration version is available to evaluate against."
            )

        evaluation_result = await self._preview_evaluation.execute(
            checklist_answers=answers,
            scoring_profile=scoring_profile,
            configuration_version_id=configuration_version.id,
        )

        evaluation_snapshot = build_evaluation_snapshot(
            trade_id=trade.id,
            configuration_version_id=configuration_version.id,
            evaluation_result=evaluation_result,
        )
        checklist_snapshot = ChecklistSnapshot(trade_id=trade.id, answers=answers)

        await self._trades.update(trade)
        await self._session.flush()
        await self._checklist_snapshots.add(checklist_snapshot)
        await self._evaluation_snapshots.add(evaluation_snapshot)

        await self._dispatcher.publish(
            DomainEvent(
                event_type="TradeOpened",
                aggregate_type="Trade",
                aggregate_id=trade.id,
                payload={"entry_price": trade.entry_price},
            ),
            self._session,
        )
        await self._dispatcher.publish(
            DomainEvent(
                event_type="TradeEvaluated",
                aggregate_type="Trade",
                aggregate_id=trade.id,
                payload={"configuration_version_id": str(configuration_version.id)},
            ),
            self._session,
        )

        return OpenTradeResult(trade=trade, evaluation=evaluation_snapshot)
