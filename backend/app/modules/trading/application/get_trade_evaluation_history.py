"""
GetTradeEvaluationHistoryUseCase — `TRADEOS_API_SPECIFICATION.md` §6.5,
`GET /trades/{id}/evaluation/history`: "every Evaluation Snapshot ever
produced for this Trade (current and superseded), each tagged with which
`configuration_version_id` produced it" — the mechanism that makes DI-06/
DI-07's reproducibility guarantee inspectable, per that section's own
framing.
"""

import uuid

from app.modules.trading.domain.evaluation_snapshot import EvaluationSnapshot
from app.modules.trading.infrastructure.repository import (
    EvaluationSnapshotRepository,
    TradeRepository,
)
from app.platform.errors import NotFoundError


class GetTradeEvaluationHistoryUseCase:
    def __init__(
        self,
        trade_repository: TradeRepository,
        evaluation_snapshot_repository: EvaluationSnapshotRepository,
    ) -> None:
        self._trades = trade_repository
        self._evaluation_snapshots = evaluation_snapshot_repository

    async def execute(self, trade_id: uuid.UUID, user_id: uuid.UUID) -> list[EvaluationSnapshot]:
        trade = await self._trades.get_by_id(trade_id)
        if trade is None or trade.user_id != user_id or trade.deleted_at is not None:
            raise NotFoundError(f"No trade with id '{trade_id}'.")

        return await self._evaluation_snapshots.list_by_trade_id(trade_id)
