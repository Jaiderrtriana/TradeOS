"""
Trading infrastructure: repositories for the `trading` schema.

`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3: never imported directly from
outside this module.

Sprint 4.1 scope is registration-only (`POST /trades`) — every repository
here only needs to *write* a freshly-constructed aggregate, never update
or list one. Read/update methods (`get_by_id`, `list_all`, ...) belong to
whichever future sprint first needs them (`GET /trades`, `CloseTrade`,
...) — not added speculatively here.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.domain.checklist_snapshot import ChecklistSnapshot
from app.modules.trading.domain.evaluation_snapshot import EvaluationSnapshot
from app.modules.trading.domain.trade import Trade
from app.modules.trading.infrastructure.models import (
    ChecklistSnapshotModel,
    EvaluationSnapshotBreakdownModel,
    EvaluationSnapshotModel,
    TradeModel,
)


class TradeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, trade: Trade) -> None:
        self._session.add(
            TradeModel(
                id=trade.id,
                user_id=trade.user_id,
                strategy_id=trade.strategy_id,
                setup_id=trade.setup_id,
                session_id=trade.session_id,
                entry_trigger_id=trade.entry_trigger_id,
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
                entered_at=trade.entered_at,
                closed_at=trade.closed_at,
                created_at=trade.created_at,
                updated_at=trade.updated_at,
                deleted_at=trade.deleted_at,
                created_by_user_id=trade.created_by_user_id,
            )
        )


class ChecklistSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, snapshot: ChecklistSnapshot) -> None:
        self._session.add(
            ChecklistSnapshotModel(
                id=snapshot.id,
                trade_id=snapshot.trade_id,
                answers=snapshot.answers,
                created_at=snapshot.created_at,
            )
        )


class EvaluationSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, snapshot: EvaluationSnapshot) -> None:
        self._session.add(
            EvaluationSnapshotModel(
                id=snapshot.id,
                trade_id=snapshot.trade_id,
                configuration_version_id=snapshot.configuration_version_id,
                confidence_score=snapshot.confidence_score,
                confidence_grade=snapshot.confidence_grade,
                quality_score=snapshot.quality_score,
                quality_grade=snapshot.quality_grade,
                execution_score=snapshot.execution_score,
                execution_grade=snapshot.execution_grade,
                market_context_score=snapshot.market_context_score,
                market_context_grade=snapshot.market_context_grade,
                bias_score=snapshot.bias_score,
                is_current=snapshot.is_current,
                created_at=snapshot.created_at,
            )
        )
        # No `relationship()` is declared between EvaluationSnapshotModel
        # and EvaluationSnapshotBreakdownModel (this codebase's established
        # convention -- plain FK columns only, e.g.
        # configuration/infrastructure/models.py never declares one
        # either). Without one, SQLAlchemy's unit-of-work has no
        # dependency information to order these two INSERTs correctly on
        # its own, and the breakdown rows can be flushed before the
        # snapshot they reference -- flushing explicitly here guarantees
        # the parent row exists first (a real bug this exact sequence hit
        # during Sprint 4.1's own integration tests -- see CHANGELOG.md).
        await self._session.flush()
        for breakdown in snapshot.breakdowns:
            self._session.add(
                EvaluationSnapshotBreakdownModel(
                    id=uuid.uuid4(),
                    evaluation_snapshot_id=snapshot.id,
                    criterion_id=breakdown.criterion_id,
                    engine_type_code=breakdown.engine_type_code,
                    criterion_name_at_time=breakdown.criterion_name_at_time,
                    raw_value=breakdown.raw_value,
                    normalized_value=breakdown.normalized_value,
                    weight=breakdown.weight,
                    contribution=breakdown.contribution,
                )
            )
