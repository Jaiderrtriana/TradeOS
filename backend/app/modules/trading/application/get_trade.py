"""
GetTradeUseCase — `TRADEOS_API_SPECIFICATION.md` §6.4, `GET /trades/{id}`:
"full detail of one Trade, including its current Evaluation Snapshot...
but not its full historical breakdown" (that's `GET /trades/{id}/evaluation`,
kept separate as "a heavier payload not needed every time a Trade is
viewed" -- so this Use Case still returns the *current* snapshot's own
breakdown, just not every past snapshot). §7.4 also establishes that the
single-resource view is the only one that returns `checklist_answers` (the
list view "omits... checklist_answers, which are fetched only via the
single-resource endpoint").

404 is identical for not-found, not-owned, and soft-deleted -- same
convention as every Sprint 4.2 write action (`TRADEOS_API_SPECIFICATION.md`
§8/§14: ownership is never leaked by a different error shape).
"""

import uuid

from app.modules.trading.domain.checklist_snapshot import ChecklistSnapshot
from app.modules.trading.domain.evaluation_snapshot import EvaluationSnapshot
from app.modules.trading.domain.trade import Trade
from app.modules.trading.infrastructure.repository import (
    ChecklistSnapshotRepository,
    EvaluationSnapshotRepository,
    TradeRepository,
)
from app.platform.errors import NotFoundError


class GetTradeResult:
    def __init__(
        self, trade: Trade, checklist_snapshot: ChecklistSnapshot, evaluation: EvaluationSnapshot
    ) -> None:
        self.trade = trade
        self.checklist_snapshot = checklist_snapshot
        self.evaluation = evaluation


class GetTradeUseCase:
    def __init__(
        self,
        trade_repository: TradeRepository,
        checklist_snapshot_repository: ChecklistSnapshotRepository,
        evaluation_snapshot_repository: EvaluationSnapshotRepository,
    ) -> None:
        self._trades = trade_repository
        self._checklist_snapshots = checklist_snapshot_repository
        self._evaluation_snapshots = evaluation_snapshot_repository

    async def execute(self, trade_id: uuid.UUID, user_id: uuid.UUID) -> GetTradeResult:
        trade = await self._trades.get_by_id(trade_id)
        if trade is None or trade.user_id != user_id or trade.deleted_at is not None:
            raise NotFoundError(f"No trade with id '{trade_id}'.")

        # Every Trade owns exactly one ChecklistSnapshot and exactly one
        # current EvaluationSnapshot, maintained since RegisterTrade --
        # `None` here would be a genuine data-integrity bug elsewhere, not
        # a legitimate "not found" for a Trade that does exist, so this
        # fails loudly rather than being folded into the 404 above (same
        # convention as the router's own `_require_current_evaluation`).
        checklist_snapshot = await self._checklist_snapshots.get_by_trade_id(trade_id)
        if checklist_snapshot is None:
            raise RuntimeError(f"Trade '{trade_id}' has no ChecklistSnapshot.")

        evaluation = await self._evaluation_snapshots.get_current_by_trade_id(trade_id)
        if evaluation is None:
            raise RuntimeError(f"Trade '{trade_id}' has no current EvaluationSnapshot.")

        return GetTradeResult(
            trade=trade, checklist_snapshot=checklist_snapshot, evaluation=evaluation
        )
