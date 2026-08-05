"""
Trading infrastructure: repositories for the `trading` schema.

`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3: never imported directly from
outside this module.

Sprint 4.1 scope was registration-only (`POST /trades`) — every
repository only wrote a freshly-constructed aggregate. Sprint 4.2 adds
the read/update methods `AmendTrade`/`CloseTrade`/`ReevaluateTrade`/
`DeleteTrade` need (`get_by_id`, `get_by_id_for_update`, `update`, ...) —
still no `list_all` here: `GET /trades` remains out of this sprint's
approved scope (Master Plan Sprint 4.2 names only the four write
actions).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.domain.checklist_snapshot import ChecklistSnapshot
from app.modules.trading.domain.evaluation_snapshot import (
    EvaluationSnapshot,
    EvaluationSnapshotBreakdown,
)
from app.modules.trading.domain.trade import PLANNED, Trade
from app.modules.trading.domain.trade_mistake import TradeMistake
from app.modules.trading.infrastructure.models import (
    ChecklistSnapshotModel,
    EvaluationSnapshotBreakdownModel,
    EvaluationSnapshotModel,
    TradeMistakeModel,
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
                status=trade.status,
                entry_price=trade.entry_price,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                exit_price=trade.exit_price,
                size=trade.size,
                margin_used=trade.margin_used,
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

    async def get_by_id(self, trade_id: uuid.UUID) -> Trade | None:
        result = await self._session.execute(select(TradeModel).where(TradeModel.id == trade_id))
        row = result.scalar_one_or_none()
        return _trade_to_domain(row) if row is not None else None

    async def get_by_id_for_update(self, trade_id: uuid.UUID) -> Trade | None:
        """`SELECT ... FOR UPDATE` — serializes concurrent
        `ReevaluateTrade` calls against the *same* Trade row. Correct here
        (unlike Configuration's `pg_advisory_xact_lock` for "the published
        version") because a Trade's identity is stable: the row being
        locked is always the same row for the lifetime of this lock,
        never shifting to a different row mid-flight
        (`ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md` §5's reasoning for
        *why* an advisory lock was needed there does not apply here)."""
        result = await self._session.execute(
            select(TradeModel).where(TradeModel.id == trade_id).with_for_update()
        )
        row = result.scalar_one_or_none()
        return _trade_to_domain(row) if row is not None else None

    async def update(self, trade: Trade) -> None:
        """A full overwrite of every mutable column, not a partial patch
        at this layer — `AmendTradeUseCase` already re-validates the
        *complete* proposed state before calling this, so there is no
        partial-write risk in saving all fields unconditionally."""
        result = await self._session.execute(select(TradeModel).where(TradeModel.id == trade.id))
        row = result.scalar_one()
        row.strategy_id = trade.strategy_id
        row.setup_id = trade.setup_id
        row.session_id = trade.session_id
        row.entry_trigger_id = trade.entry_trigger_id
        row.market = trade.market
        row.direction = trade.direction
        row.status = trade.status
        row.entry_price = trade.entry_price
        row.stop_loss = trade.stop_loss
        row.take_profit = trade.take_profit
        row.exit_price = trade.exit_price
        row.size = trade.size
        row.margin_used = trade.margin_used
        row.leverage = trade.leverage
        row.result = trade.result
        row.realized_pnl = trade.realized_pnl
        row.mfe_price = trade.mfe_price
        row.mae_price = trade.mae_price
        row.notes = trade.notes
        row.entered_at = trade.entered_at
        row.closed_at = trade.closed_at
        row.updated_at = trade.updated_at
        row.deleted_at = trade.deleted_at

    async def list_all(
        self,
        *,
        user_id: uuid.UUID,
        direction: str | None = None,
        status: str | None = None,
        result: str | None = None,
        entered_after: datetime | None = None,
        entered_before: datetime | None = None,
        strategy_id: uuid.UUID | None = None,
        setup_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        entry_trigger_id: uuid.UUID | None = None,
        sort_descending: bool = True,
        cursor: "TradeListCursor | None" = None,
        limit: int = 50,
    ) -> list[Trade]:
        """`GET /trades` (`TRADEOS_API_SPECIFICATION.md` §6.4/§7). Keyset
        (never offset) pagination on `(entered_at, id)` -- §7.4 explicitly
        rejects offset pagination ("produces incorrect results under
        concurrent writes"), so a page boundary is a `WHERE` predicate on
        the last row's own sort key, never a `LIMIT/OFFSET` that a
        concurrent insert could shift. `entered_at` is the only sort
        field implemented -- the one literal example given (§7.1:
        `sort=-entered_at`) and this table's own documented default
        (§7.2); no other sort field is named anywhere for Trades, so none
        is invented here.

        Always scoped to `user_id` and `deleted_at IS NULL` -- ownership
        (§4.6) and the same "soft-deleted behaves as excluded" convention
        every Sprint 4.2 write action already applies.
        """
        query = select(TradeModel).where(
            TradeModel.user_id == user_id, TradeModel.deleted_at.is_(None)
        )
        if direction is not None:
            query = query.where(TradeModel.direction == direction)
        if status is not None:
            query = query.where(TradeModel.status == status)
        if result is not None:
            query = query.where(TradeModel.result == result)
        if entered_after is not None:
            query = query.where(TradeModel.entered_at >= entered_after)
        if entered_before is not None:
            query = query.where(TradeModel.entered_at <= entered_before)
        if strategy_id is not None:
            query = query.where(TradeModel.strategy_id == strategy_id)
        if setup_id is not None:
            query = query.where(TradeModel.setup_id == setup_id)
        if session_id is not None:
            query = query.where(TradeModel.session_id == session_id)
        if entry_trigger_id is not None:
            query = query.where(TradeModel.entry_trigger_id == entry_trigger_id)

        if cursor is not None:
            if sort_descending:
                query = query.where(
                    or_(
                        TradeModel.entered_at < cursor.entered_at,
                        and_(
                            TradeModel.entered_at == cursor.entered_at,
                            TradeModel.id < cursor.id,
                        ),
                    )
                )
            else:
                query = query.where(
                    or_(
                        TradeModel.entered_at > cursor.entered_at,
                        and_(
                            TradeModel.entered_at == cursor.entered_at,
                            TradeModel.id > cursor.id,
                        ),
                    )
                )

        if sort_descending:
            query = query.order_by(TradeModel.entered_at.desc(), TradeModel.id.desc())
        else:
            query = query.order_by(TradeModel.entered_at.asc(), TradeModel.id.asc())

        query = query.limit(limit)
        result_rows = await self._session.execute(query)
        return [_trade_to_domain(row) for row in result_rows.scalars()]

    async def list_all_facts_for_statistics(
        self, user_id: uuid.UUID
    ) -> list["TradeStatisticsFact"]:
        """`StatisticsAggregationService` (Sprint 6.1): every one of this
        user's non-deleted Trades, in one unbounded query -- never cursor-
        paginated like `list_all` above, since an all-time aggregation
        needs the complete set, not one page of it. Only the raw columns
        the aggregation actually needs (`TRADEOS_DATABASE_DESIGN.md`
        §6.9) -- `r_multiple` is computed later, by the caller, via
        `compute_r_multiple` (never duplicated here); Evaluation scores
        are a separate batched read (`EvaluationSnapshotRepository.
        list_current_by_trade_ids`), not this query's concern.

        `entered_at` (Sprint 6.2) is included so Rolling Statistics can
        select "the most recent N Trades" (`TRADEOS_DOMAIN_MODEL.md`
        §2.3) without a second query -- the same already-indexed column
        `list_all` above orders by (`TRADEOS_DATABASE_DESIGN.md` §6.9's
        "Analytics' time-based queries" index).

        v2.0 (Domain Model DI-13): `status = 'planned'` rows are excluded
        at the query itself, not filtered later by the caller -- a
        Planned Trade must never enter *any* Statistics metric, including
        a future "Total Trades" count."""
        result = await self._session.execute(
            select(
                TradeModel.id,
                TradeModel.direction,
                TradeModel.result,
                TradeModel.realized_pnl,
                TradeModel.entry_price,
                TradeModel.stop_loss,
                TradeModel.exit_price,
                TradeModel.strategy_id,
                TradeModel.setup_id,
                TradeModel.session_id,
                TradeModel.entered_at,
            ).where(
                TradeModel.user_id == user_id,
                TradeModel.deleted_at.is_(None),
                TradeModel.status != PLANNED,
            )
        )
        return [
            TradeStatisticsFact(
                id=row.id,
                direction=row.direction,
                result=row.result,
                realized_pnl=_as_float(row.realized_pnl),
                entry_price=_as_float(row.entry_price),
                stop_loss=_as_float(row.stop_loss),
                exit_price=_as_optional_float(row.exit_price),
                strategy_id=row.strategy_id,
                setup_id=row.setup_id,
                session_id=row.session_id,
                entered_at=row.entered_at,
            )
            for row in result.all()
        ]


@dataclass(frozen=True)
class TradeListCursor:
    """The opaque `?cursor=` value's decoded form -- see
    `trading/presentation/pagination.py` for its base64/JSON encoding.
    Kept as a plain keyset tuple `(entered_at, id)`, never an offset."""

    entered_at: datetime
    id: uuid.UUID


@dataclass(frozen=True)
class TradeStatisticsFact:
    """One Trade's raw fields for `StatisticsAggregationService` --
    exactly what `compute_r_multiple` and the by-dimension grouping need,
    nothing else. Kept in `infrastructure/` (not `domain/`), same
    reasoning as `MistakeTradeFact` (Sprint 5.2): a query-result shape,
    not a domain concept. `trading/application/list_trade_statistics_
    facts.py` enriches it with `r_multiple` and Evaluation scores before
    handing it to Statistics' own domain layer.

    v2.0: `result` is `None` for an `Open` Trade (`'open'` retired as a
    result value) -- `Planned` Trades never reach this dataclass at all
    (excluded at the query in `list_all_facts_for_statistics` above), so
    every row here is either `Open` (`result is None`) or `Closed`
    (`result` is `tp`/`sl`/`be`)."""

    id: uuid.UUID
    direction: str
    result: str | None
    realized_pnl: float
    entry_price: float
    stop_loss: float
    exit_price: float | None
    strategy_id: uuid.UUID | None
    setup_id: uuid.UUID | None
    session_id: uuid.UUID | None
    entered_at: datetime


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

    async def get_by_trade_id(self, trade_id: uuid.UUID) -> ChecklistSnapshot | None:
        result = await self._session.execute(
            select(ChecklistSnapshotModel).where(ChecklistSnapshotModel.trade_id == trade_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return ChecklistSnapshot(
            id=row.id, trade_id=row.trade_id, answers=row.answers, created_at=row.created_at
        )


class EvaluationSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current_snapshot_id(self, trade_id: uuid.UUID) -> uuid.UUID | None:
        result = await self._session.execute(
            select(EvaluationSnapshotModel.id).where(
                EvaluationSnapshotModel.trade_id == trade_id,
                EvaluationSnapshotModel.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_current_by_trade_id(self, trade_id: uuid.UUID) -> EvaluationSnapshot | None:
        """Full read (snapshot + breakdown rows), for `AmendTrade`'s and
        `CloseTrade`'s own `TradeResponse.evaluation` (§6.4's "the updated
        Trade" response already embeds the current Evaluation Snapshot,
        matching §7.6's general "GET /trades/{id} always embeds the
        current Evaluation Snapshot summary" principle). Exactly two
        queries regardless of how many breakdown rows exist -- not one
        query per row."""
        snapshot_result = await self._session.execute(
            select(EvaluationSnapshotModel).where(
                EvaluationSnapshotModel.trade_id == trade_id,
                EvaluationSnapshotModel.is_current.is_(True),
            )
        )
        snapshot_row = snapshot_result.scalar_one_or_none()
        if snapshot_row is None:
            return None

        breakdown_result = await self._session.execute(
            select(EvaluationSnapshotBreakdownModel).where(
                EvaluationSnapshotBreakdownModel.evaluation_snapshot_id == snapshot_row.id
            )
        )
        # Same Decimal-vs-float mapping discipline as `_trade_to_domain`
        # below -- Numeric columns come back as `decimal.Decimal`.
        breakdowns = [
            EvaluationSnapshotBreakdown(
                criterion_id=row.criterion_id,
                engine_type_code=row.engine_type_code,
                criterion_name_at_time=row.criterion_name_at_time,
                raw_value=row.raw_value,
                normalized_value=_as_float(row.normalized_value),
                weight=_as_float(row.weight),
                contribution=_as_float(row.contribution),
            )
            for row in breakdown_result.scalars()
        ]

        return EvaluationSnapshot(
            id=snapshot_row.id,
            trade_id=snapshot_row.trade_id,
            configuration_version_id=snapshot_row.configuration_version_id,
            confidence_score=_as_optional_float(snapshot_row.confidence_score),
            confidence_grade=snapshot_row.confidence_grade,
            quality_score=_as_optional_float(snapshot_row.quality_score),
            quality_grade=snapshot_row.quality_grade,
            execution_score=_as_optional_float(snapshot_row.execution_score),
            execution_grade=snapshot_row.execution_grade,
            market_context_score=_as_optional_float(snapshot_row.market_context_score),
            market_context_grade=snapshot_row.market_context_grade,
            bias_score=_as_optional_float(snapshot_row.bias_score),
            is_current=snapshot_row.is_current,
            created_at=snapshot_row.created_at,
            breakdowns=breakdowns,
        )

    async def list_current_by_trade_ids(
        self, trade_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, EvaluationSnapshot]:
        """`GET /trades`'s own batch read: one query for the current
        snapshot of every Trade on the page, never one query per row
        (N+1 avoidance, same discipline as `PreviewEvaluationUseCase`'s
        own audited query count). Breakdown rows are deliberately never
        fetched here -- §7.4: list summaries "omit
        evaluation_snapshot_breakdowns... to keep list responses cheap"
        -- so each returned `EvaluationSnapshot.breakdowns` is an empty
        list; callers building a list-item response must only read the
        score/grade fields, never `.breakdowns`, from this method's
        result."""
        if not trade_ids:
            return {}
        result = await self._session.execute(
            select(EvaluationSnapshotModel).where(
                EvaluationSnapshotModel.trade_id.in_(trade_ids),
                EvaluationSnapshotModel.is_current.is_(True),
            )
        )
        return {
            row.trade_id: EvaluationSnapshot(
                id=row.id,
                trade_id=row.trade_id,
                configuration_version_id=row.configuration_version_id,
                confidence_score=_as_optional_float(row.confidence_score),
                confidence_grade=row.confidence_grade,
                quality_score=_as_optional_float(row.quality_score),
                quality_grade=row.quality_grade,
                execution_score=_as_optional_float(row.execution_score),
                execution_grade=row.execution_grade,
                market_context_score=_as_optional_float(row.market_context_score),
                market_context_grade=row.market_context_grade,
                bias_score=_as_optional_float(row.bias_score),
                is_current=row.is_current,
                created_at=row.created_at,
                breakdowns=[],
            )
            for row in result.scalars()
        }

    async def list_by_trade_id(self, trade_id: uuid.UUID) -> list[EvaluationSnapshot]:
        """`GET /trades/{id}/evaluation/history` (§6.5): "every Evaluation
        Snapshot ever produced for this Trade... ordered newest first."
        Exactly two queries regardless of how many snapshots or breakdown
        rows exist -- one for every snapshot row, one for every breakdown
        row across all of them (grouped in Python by `evaluation_snapshot_id`),
        never one breakdown query per snapshot."""
        snapshot_result = await self._session.execute(
            select(EvaluationSnapshotModel)
            .where(EvaluationSnapshotModel.trade_id == trade_id)
            .order_by(EvaluationSnapshotModel.created_at.desc())
        )
        snapshot_rows = list(snapshot_result.scalars())
        if not snapshot_rows:
            return []

        breakdown_result = await self._session.execute(
            select(EvaluationSnapshotBreakdownModel).where(
                EvaluationSnapshotBreakdownModel.evaluation_snapshot_id.in_(
                    [row.id for row in snapshot_rows]
                )
            )
        )
        breakdowns_by_snapshot_id: dict[uuid.UUID, list[EvaluationSnapshotBreakdown]] = {}
        for row in breakdown_result.scalars():
            breakdowns_by_snapshot_id.setdefault(row.evaluation_snapshot_id, []).append(
                EvaluationSnapshotBreakdown(
                    criterion_id=row.criterion_id,
                    engine_type_code=row.engine_type_code,
                    criterion_name_at_time=row.criterion_name_at_time,
                    raw_value=row.raw_value,
                    normalized_value=_as_float(row.normalized_value),
                    weight=_as_float(row.weight),
                    contribution=_as_float(row.contribution),
                )
            )

        return [
            EvaluationSnapshot(
                id=row.id,
                trade_id=row.trade_id,
                configuration_version_id=row.configuration_version_id,
                confidence_score=_as_optional_float(row.confidence_score),
                confidence_grade=row.confidence_grade,
                quality_score=_as_optional_float(row.quality_score),
                quality_grade=row.quality_grade,
                execution_score=_as_optional_float(row.execution_score),
                execution_grade=row.execution_grade,
                market_context_score=_as_optional_float(row.market_context_score),
                market_context_grade=row.market_context_grade,
                bias_score=_as_optional_float(row.bias_score),
                is_current=row.is_current,
                created_at=row.created_at,
                breakdowns=breakdowns_by_snapshot_id.get(row.id, []),
            )
            for row in snapshot_rows
        ]

    async def mark_not_current(self, evaluation_snapshot_id: uuid.UUID) -> None:
        """Must be called -- and its flush observed -- *before* the new
        snapshot is added: `ix_evaluation_snapshots_one_current_per_trade`
        is a plain, non-deferrable partial unique index, so inserting the
        new current row before superseding the old one would momentarily
        leave two `is_current = true` rows for the same trade within this
        same transaction, tripping the constraint immediately -- the exact
        self-conflict class of bug already found and fixed in
        `PublishScoringConfigurationVersionUseCase` (see CHANGELOG.md)."""
        result = await self._session.execute(
            select(EvaluationSnapshotModel).where(
                EvaluationSnapshotModel.id == evaluation_snapshot_id
            )
        )
        row = result.scalar_one()
        row.is_current = False
        await self._session.flush()

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


class TradeMistakeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, trade_mistake: TradeMistake) -> None:
        """No existence check first -- the composite primary key
        `(trade_id, catalog_entry_id)` is the concurrency-safety
        mechanism itself. A duplicate tag attempt raises `IntegrityError`
        on flush, which `TagMistakeUseCase` translates to `ConflictError`
        -- never a "SELECT to check, then INSERT" sequence (the exact
        race `ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md` diagnosed and
        fixed for Configuration's publish flow)."""
        self._session.add(
            TradeMistakeModel(
                trade_id=trade_mistake.trade_id,
                catalog_entry_id=trade_mistake.catalog_entry_id,
                created_at=trade_mistake.created_at,
            )
        )

    async def list_by_trade_id(self, trade_id: uuid.UUID) -> list[TradeMistake]:
        """`GET /trades/{id}/mistakes`: every Mistake Tag currently attached
        to this Trade. One query, ordered newest-first (matching the
        pagination/history ordering convention already used everywhere
        else in this module)."""
        result = await self._session.execute(
            select(TradeMistakeModel)
            .where(TradeMistakeModel.trade_id == trade_id)
            .order_by(TradeMistakeModel.created_at.desc())
        )
        return [
            TradeMistake(
                trade_id=row.trade_id,
                catalog_entry_id=row.catalog_entry_id,
                created_at=row.created_at,
            )
            for row in result.scalars()
        ]

    async def list_trade_facts_for_ranking(self, user_id: uuid.UUID) -> list["MistakeTradeFact"]:
        """`MistakePriorityRankingService` (Sprint 5.2): every `trade_
        mistakes` row for this user's Trades, joined with the raw Trade
        fields `compute_r_multiple` needs -- one query, never one per
        Trade (the N+1 `TradeRepository.list_all` + per-trade `list_by_
        trade_id` would produce). Scoped to `user_id` via the join, not a
        separate ownership check -- a soft-deleted Trade is excluded the
        same way every other read in this module already excludes one."""
        result = await self._session.execute(
            select(
                TradeMistakeModel.catalog_entry_id,
                TradeModel.direction,
                TradeModel.entry_price,
                TradeModel.stop_loss,
                TradeModel.exit_price,
            )
            .join(TradeModel, TradeMistakeModel.trade_id == TradeModel.id)
            .where(TradeModel.user_id == user_id, TradeModel.deleted_at.is_(None))
        )
        return [
            MistakeTradeFact(
                catalog_entry_id=row.catalog_entry_id,
                direction=row.direction,
                entry_price=_as_float(row.entry_price),
                stop_loss=_as_float(row.stop_loss),
                exit_price=_as_optional_float(row.exit_price),
            )
            for row in result.all()
        ]


@dataclass(frozen=True)
class MistakeTradeFact:
    """One `trade_mistakes` occurrence's raw Trade fields -- exactly what
    `compute_r_multiple` needs, nothing else. Kept in `infrastructure/`
    (not `domain/`) since it's a query-result shape, not a domain
    concept; `trading/application/list_mistake_occurrences.py` converts
    it into the cost figure Mistakes' own domain layer actually uses."""

    catalog_entry_id: uuid.UUID
    direction: str
    entry_price: float
    stop_loss: float
    exit_price: float | None


def _as_float(value: Any) -> float:
    return float(value)


def _as_optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _trade_to_domain(row: TradeModel) -> Trade:
    # asyncpg/SQLAlchemy maps a `Numeric` column to `decimal.Decimal`, not
    # `float` -- a freshly-constructed Trade (RegisterTradeUseCase, never
    # round-tripped through the database) only ever holds plain `float`s,
    # so a Trade read back via this mapper must be cast explicitly, or its
    # own computed properties break the moment they mix a DB-loaded
    # `Decimal` with a `float` supplied fresh by a later request (e.g.
    # AmendTrade patching one field while every other one is still
    # `Decimal` from this read) -- a real bug Sprint 4.2's own integration
    # tests caught (see CHANGELOG.md), since Sprint 4.1 never exercised
    # this repository's read path at all.
    return Trade(
        id=row.id,
        user_id=row.user_id,
        strategy_id=row.strategy_id,
        setup_id=row.setup_id,
        session_id=row.session_id,
        entry_trigger_id=row.entry_trigger_id,
        market=row.market,
        direction=row.direction,
        status=row.status,
        entry_price=_as_optional_float(row.entry_price),
        stop_loss=_as_optional_float(row.stop_loss),
        take_profit=_as_optional_float(row.take_profit),
        exit_price=_as_optional_float(row.exit_price),
        size=_as_float(row.size),
        margin_used=_as_optional_float(row.margin_used),
        leverage=row.leverage,
        result=row.result,
        realized_pnl=_as_float(row.realized_pnl),
        mfe_price=_as_optional_float(row.mfe_price),
        mae_price=_as_optional_float(row.mae_price),
        notes=row.notes,
        entered_at=row.entered_at,
        closed_at=row.closed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        created_by_user_id=row.created_by_user_id,
    )
