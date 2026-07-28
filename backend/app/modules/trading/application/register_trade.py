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

`closed_at` (approved resolution, Sprint 4.1 — no document names a
`closed_at` input field, yet INV-TRADE-02 requires one whenever
`result != open`): set to `now()` here, at the moment the transaction is
processed, whenever `result != open` and `exit_price` is supplied — never
accepted from the request. Composes with `Trade.__post_init__` for free:
if `result != open` but no `exit_price` was supplied, `closed_at` stays
`None` too, and INV-TRADE-02 correctly rejects it as incomplete (the
documented 422, "missing exit_price").

`scoring_profile` (approved resolution, Sprint 4.1 — API Specification
originally omitted this field from `POST /trades`, even though the
Evaluation call this Use Case makes requires one): now a required field
of the request, propagated verbatim to `PreviewEvaluationUseCase` —
never defaulted, never read from a preference. See CHANGELOG.md.

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
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.get_catalog_entry import GetCatalogEntryUseCase
from app.modules.configuration.application.get_configuration_version import (
    GetConfigurationVersionUseCase,
)
from app.modules.evaluation.application.preview_evaluation import PreviewEvaluationUseCase
from app.modules.trading.domain.checklist_snapshot import ChecklistSnapshot
from app.modules.trading.domain.evaluation_snapshot import (
    EvaluationSnapshot,
    EvaluationSnapshotBreakdown,
)
from app.modules.trading.domain.trade import OPEN, Trade
from app.modules.trading.infrastructure.repository import (
    ChecklistSnapshotRepository,
    EvaluationSnapshotRepository,
    TradeRepository,
)
from app.platform.errors import UnprocessableEntityError
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher

_GRADED_ENGINES = ("confidence", "quality", "execution", "market_context")


class RegisterTradeResult:
    def __init__(self, trade: Trade, evaluation: EvaluationSnapshot) -> None:
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
        entry_price: float,
        stop_loss: float,
        scoring_profile: str,
        exit_price: float | None = None,
        size: float = 0,
        leverage: str = "",
        result: str = OPEN,
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

        closed_at = (
            datetime.now(timezone.utc) if result != OPEN and exit_price is not None else None
        )

        trade = Trade(
            user_id=user_id,
            market=market,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            strategy_id=strategy_id,
            setup_id=setup_id,
            session_id=session_id,
            entry_trigger_id=entry_trigger_id,
            exit_price=exit_price,
            size=size,
            leverage=leverage,
            result=result,
            mfe_price=mfe_price,
            mae_price=mae_price,
            notes=notes,
            closed_at=closed_at,
            created_by_user_id=user_id,
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

        breakdowns: list[EvaluationSnapshotBreakdown] = []
        for engine_type_code in _GRADED_ENGINES:
            engine_result = getattr(evaluation_result, engine_type_code)
            breakdowns.extend(_breakdown_rows(engine_type_code, engine_result.breakdown))
        breakdowns.extend(_breakdown_rows("bias", evaluation_result.bias.breakdown))

        evaluation_snapshot = EvaluationSnapshot(
            trade_id=trade.id,
            configuration_version_id=configuration_version.id,
            confidence_score=evaluation_result.confidence.score.value,
            confidence_grade=_grade_value(evaluation_result.confidence.score.grade),
            quality_score=evaluation_result.quality.score.value,
            quality_grade=_grade_value(evaluation_result.quality.score.grade),
            execution_score=evaluation_result.execution.score.value,
            execution_grade=_grade_value(evaluation_result.execution.score.grade),
            market_context_score=evaluation_result.market_context.score.value,
            market_context_grade=_grade_value(evaluation_result.market_context.score.grade),
            bias_score=evaluation_result.bias.score.value,
            breakdowns=breakdowns,
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
        await self._checklist_snapshots.add(checklist_snapshot)
        await self._evaluation_snapshots.add(evaluation_snapshot)

        await self._dispatcher.publish(
            DomainEvent(
                event_type="TradeRegistered",
                aggregate_type="Trade",
                aggregate_id=trade.id,
                payload={
                    "market": trade.market,
                    "direction": trade.direction,
                    "result": trade.result,
                },
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


def _grade_value(grade: Any) -> str | None:
    return grade.value if grade is not None else None


def _breakdown_rows(engine_type_code: str, rows: list[Any]) -> list[EvaluationSnapshotBreakdown]:
    return [
        EvaluationSnapshotBreakdown(
            criterion_id=row.criterion_id,
            engine_type_code=engine_type_code,
            criterion_name_at_time=row.criterion_name,
            raw_value=row.raw_value,
            normalized_value=row.normalized_value,
            weight=row.weight,
            contribution=row.contribution,
        )
        for row in rows
    ]
