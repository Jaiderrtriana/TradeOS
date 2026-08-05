"""
RegisterTradeUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §4.1;
`TRADEOS_API_SPECIFICATION.md` §6.4, `POST /trades`; flow traced in §11.1.

Business Flow (literal order from §4.1): validate shape (Pydantic, at the
presentation layer) -> validate INV-TRADE-01 (stop placement) -> validate
INV-TRADE-02 (result+exit_price together) -> call Evaluation's
Application-layer service with `checklist_answers` and the active
`ScoringConfiguration` -> persist Trade + ChecklistSnapshot +
EvaluationSnapshot (+ breakdown rows) in one transaction -> publish
`TradeRegistered`, then `TradeEvaluated`.

v2.0 (Trade Entry redesign, Domain Model KDD-07): `status` is now a
required, explicit field with no default. `closed_at` (like
`entry_price`/`entered_at`/`exit_price`/`result`/`realized_pnl`) is a
trader-supplied fact accepted directly from the request whenever
`status = closed` — no longer computed as `now()` server-side (Sprint
4.1's original resolution), since a `Closed` Trade can now be entered
retroactively (e.g. backfilling historical trades) with its real close
timestamp. `Trade.__post_init__`'s `validate_status_fields` still
enforces that every field required by a given `status` is present.

`scoring_profile` (Sprint 4.1's original resolution: always required)
is now required **only once `status != planned`** (API Specification
§6.4) — a `Planned` Trade has no Checklist/Evaluation yet by definition
(Domain Invariant DI-13), so this Use Case skips the entire Evaluation
flow (no `ChecklistSnapshot`, no `EvaluationSnapshot`, no
`TradeEvaluated` event) when `status = planned`. Evaluation runs for the
first time either here (Trade created directly as `Open`/`Closed`) or in
`OpenTradeUseCase` (a Trade that started `Planned`) — never twice.

Catalog reference validation (Preconditions, §4.1): each of
`strategy_id`/`setup_id`/`session_id`/`entry_trigger_id`, if supplied,
must reference an existing, active `CatalogEntry` — checked via
Configuration's `GetCatalogEntryUseCase` factory. Matching `kind` (e.g.
`strategy_id` actually pointing at a `kind=strategy` row) is not
cross-validated — the frozen docs' own precondition wording is only
"exist and are active," not kind-matching; treated as a deliberate
literal reading, not an oversight (see CHANGELOG.md).

Cross-module reads happen exclusively through Configuration's and
Evaluation's own `build_*` Application-layer factories (never their
domain/infrastructure layers directly, `TRADEOS_SYSTEM_ARCHITECTURE.md`
§3.3) — including the `EvaluationResult` `PreviewEvaluationUseCase`
returns: this Use Case reads its attributes structurally, exactly as
`PreviewEvaluationUseCase` itself already does with Configuration's
`ScoringConfigurationVersion` (see `preview_evaluation.py`), never
importing `app.modules.evaluation.domain.*` to type it.

The configuration version is resolved exactly once (`GetConfigurationVersionUseCase`,
already existing since Sprint 3.2) and its `id` is then passed explicitly
into `PreviewEvaluationUseCase.execute()` — not left to resolve
`get_published()` a second time independently — so the `EvaluationSnapshot`
persisted here is guaranteed to reference the exact same version that
actually produced its scores, even if a publish happens to land in
between two independent reads.
"""

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.get_catalog_entry import GetCatalogEntryUseCase
from app.modules.configuration.application.get_configuration_version import (
    GetConfigurationVersionUseCase,
)
from app.modules.evaluation.application.preview_evaluation import PreviewEvaluationUseCase
from app.modules.trading.application.evaluation_snapshot_mapping import build_evaluation_snapshot
from app.modules.trading.domain.checklist_snapshot import ChecklistSnapshot
from app.modules.trading.domain.evaluation_snapshot import EvaluationSnapshot
from app.modules.trading.domain.trade import PLANNED, Trade
from app.modules.trading.infrastructure.repository import (
    ChecklistSnapshotRepository,
    EvaluationSnapshotRepository,
    TradeRepository,
)
from app.platform.errors import UnprocessableEntityError
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher


class RegisterTradeResult:
    def __init__(self, trade: Trade, evaluation: EvaluationSnapshot | None) -> None:
        self.trade = trade
        self.evaluation = evaluation


class RegisterTradeUseCase:
    def __init__(
        self,
        trade_repository: TradeRepository,
        checklist_snapshot_repository: ChecklistSnapshotRepository,
        evaluation_snapshot_repository: EvaluationSnapshotRepository,
        get_catalog_entry_use_case: GetCatalogEntryUseCase,
        get_configuration_version_use_case: GetConfigurationVersionUseCase,
        preview_evaluation_use_case: PreviewEvaluationUseCase,
        dispatcher: EventDispatcher,
        session: AsyncSession,
    ) -> None:
        self._trades = trade_repository
        self._checklist_snapshots = checklist_snapshot_repository
        self._evaluation_snapshots = evaluation_snapshot_repository
        self._get_catalog_entry = get_catalog_entry_use_case
        self._get_configuration_version = get_configuration_version_use_case
        self._preview_evaluation = preview_evaluation_use_case
        self._dispatcher = dispatcher
        self._session = session

    async def execute(
        self,
        *,
        user_id: uuid.UUID,
        market: str,
        direction: str,
        status: str,
        scoring_profile: str | None = None,
        entry_price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        entered_at: datetime | None = None,
        exit_price: float | None = None,
        result: str | None = None,
        closed_at: datetime | None = None,
        realized_pnl: float = 0,
        size: float = 0,
        margin_used: float | None = None,
        leverage: str = "",
        strategy_id: uuid.UUID | None = None,
        setup_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        entry_trigger_id: uuid.UUID | None = None,
        notes: str = "",
        mfe_price: float | None = None,
        mae_price: float | None = None,
        checklist_answers: dict[str, str | float] | None = None,
    ) -> RegisterTradeResult:
        await self._validate_catalog_reference("strategy_id", strategy_id)
        await self._validate_catalog_reference("setup_id", setup_id)
        await self._validate_catalog_reference("session_id", session_id)
        await self._validate_catalog_reference("entry_trigger_id", entry_trigger_id)

        trade = Trade(
            user_id=user_id,
            market=market,
            direction=direction,
            status=status,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_id=strategy_id,
            setup_id=setup_id,
            session_id=session_id,
            entry_trigger_id=entry_trigger_id,
            exit_price=exit_price,
            size=size,
            margin_used=margin_used,
            leverage=leverage,
            result=result,
            realized_pnl=realized_pnl,
            mfe_price=mfe_price,
            mae_price=mae_price,
            notes=notes,
            entered_at=entered_at,
            closed_at=closed_at,
            created_by_user_id=user_id,
        )

        evaluation_snapshot: EvaluationSnapshot | None = None
        checklist_snapshot: ChecklistSnapshot | None = None
        configuration_version_id: uuid.UUID | None = None

        # DI-13: a Planned Trade has no Checklist/Evaluation yet by
        # definition -- Evaluation runs here for every other status, and
        # is deferred to `OpenTradeUseCase` for a Trade that started
        # Planned (API Specification §6.4).
        if status != PLANNED:
            if scoring_profile is None:
                raise UnprocessableEntityError(
                    "'scoring_profile' is required once status is not 'planned'."
                )
            answers = checklist_answers or {}

            configuration_version = await self._get_configuration_version.execute()
            if configuration_version is None:
                raise UnprocessableEntityError(
                    "No configuration version is available to evaluate against."
                )
            configuration_version_id = configuration_version.id

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

        await self._trades.add(trade)
        # Flushed before the two children below are even added: no
        # `relationship()` links TradeModel to ChecklistSnapshotModel/
        # EvaluationSnapshotModel (plain FK columns only, matching this
        # codebase's established convention), so SQLAlchemy's
        # unit-of-work has no dependency information to insert `trades`
        # before its children on its own -- see
        # `EvaluationSnapshotRepository.add()`'s own flush for the exact
        # same reason.
        await self._session.flush()
        if checklist_snapshot is not None:
            await self._checklist_snapshots.add(checklist_snapshot)
        if evaluation_snapshot is not None:
            await self._evaluation_snapshots.add(evaluation_snapshot)

        await self._dispatcher.publish(
            DomainEvent(
                event_type="TradeRegistered",
                aggregate_type="Trade",
                aggregate_id=trade.id,
                payload={
                    "market": trade.market,
                    "direction": trade.direction,
                    "status": trade.status,
                },
            ),
            self._session,
        )
        if evaluation_snapshot is not None:
            await self._dispatcher.publish(
                DomainEvent(
                    event_type="TradeEvaluated",
                    aggregate_type="Trade",
                    aggregate_id=trade.id,
                    payload={"configuration_version_id": str(configuration_version_id)},
                ),
                self._session,
            )

        return RegisterTradeResult(trade=trade, evaluation=evaluation_snapshot)

    async def _validate_catalog_reference(
        self, field_name: str, entry_id: uuid.UUID | None
    ) -> None:
        if entry_id is None:
            return
        entry = await self._get_catalog_entry.execute(entry_id)
        if entry is None or not entry.is_active:
            raise UnprocessableEntityError(
                f"'{field_name}' references a catalog entry that does not exist or is inactive."
            )
