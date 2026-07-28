"""
GetTradeEvaluationUseCase — `TRADEOS_API_SPECIFICATION.md` §6.5,
`GET /trades/{id}/evaluation`: "the current Evaluation Snapshot for a
Trade, with full criterion-level breakdown (the 'Rule Explorer')."
"""

import uuid

from app.modules.trading.domain.evaluation_snapshot import EvaluationSnapshot
from app.modules.trading.infrastructure.repository import (
    EvaluationSnapshotRepository,
    TradeRepository,
)
from app.platform.errors import NotFoundError


class GetTradeEvaluationUseCase:
    def __init__(
        self,
        trade_repository: TradeRepository,
        evaluation_snapshot_repository: EvaluationSnapshotRepository,
    ) -> None:
        self._trades = trade_repository
        self._evaluation_snapshots = evaluation_snapshot_repository

    async def execute(self, trade_id: uuid.UUID, user_id: uuid.UUID) -> EvaluationSnapshot:
        trade = await self._trades.get_by_id(trade_id)
        if trade is None or trade.user_id != user_id or trade.deleted_at is not None:
            raise NotFoundError(f"No trade with id '{trade_id}'.")

        evaluation = await self._evaluation_snapshots.get_current_by_trade_id(trade_id)
        if evaluation is None:
            raise RuntimeError(f"Trade '{trade_id}' has no current EvaluationSnapshot.")

        return evaluation
