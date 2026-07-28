"""
ReevaluateTradeUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §4.3;
`TRADEOS_API_SPECIFICATION.md` §6.4, `POST /trades/{id}/reevaluate`.

Business Flow (literal order from §4.3): load the Trade's existing
`ChecklistSnapshot` (unchanged) -> call Evaluation's service against the
specified Configuration version -> insert a **new** `EvaluationSnapshot`
row with `is_current = true` -> flip the prior row's `is_current` to
`false` (never delete it) -> publish `TradeEvaluated`.

Ordering note (applying, not rediscovering, the Sprint 3.2/ADR lesson):
the prior snapshot is flipped to not-current *before* the new one is
inserted -- `ix_evaluation_snapshots_one_current_per_trade` is the same
kind of plain, non-deferrable partial unique index that caused
`PublishScoringConfigurationVersionUseCase`'s original self-conflict bug
when the order was reversed (see CHANGELOG.md, Technical debt closed —
Configuration publish race condition). `EvaluationSnapshotRepository.
mark_not_current()` flushes internally for exactly this reason.

`scoring_profile` (approved resolution, Sprint 4.2 — same reasoning as
`POST /trades` in Sprint 4.1): a required request field, propagated
verbatim to `PreviewEvaluationUseCase`, never persisted, never defaulted,
never read from a preference. Every call into Evaluation across this
whole module (`POST /evaluation/preview`, `POST /trades`, and now this
endpoint) receives exactly the same explicit input contract.

`version.status` is compared against the literal string `"published"`
rather than importing Configuration's `PUBLISHED` domain constant --
consistent with `TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3 (never import
another module's domain layer directly). This is the same structural,
duck-typed read `PreviewEvaluationUseCase` already applies to a
`ScoringConfigurationVersion` it never imports the type of; the literal
itself is a stable wire value fixed by `TRADEOS_DATABASE_DESIGN.md`
§6.6's own check constraint (`status IN ('draft','published',
'superseded')`), not an implementation detail that could drift.

Status codes (§6.4, literal): `404` covers *both* "Trade not found" and
"specified configuration version not found" -- including when
`configuration_version_id` is omitted and no version is currently
published at all, read here as the same "the [implicitly determined]
version was not found" case. This deliberately differs from
`RegisterTradeUseCase`'s own (undocumented, Sprint 4.1's own filled-in
choice) `422` for the equivalent situation -- reevaluate has an explicit
citation for `404` that register does not, so the two are not meant to
match.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.get_configuration_version import (
    GetConfigurationVersionUseCase,
)
from app.modules.evaluation.application.preview_evaluation import PreviewEvaluationUseCase
from app.modules.trading.application.evaluation_snapshot_mapping import build_evaluation_snapshot
from app.modules.trading.domain.evaluation_snapshot import EvaluationSnapshot
from app.modules.trading.infrastructure.repository import (
    ChecklistSnapshotRepository,
    EvaluationSnapshotRepository,
    TradeRepository,
)
from app.platform.errors import NotFoundError, UnprocessableEntityError
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher

PUBLISHED = "published"


class ReevaluateTradeUseCase:
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
        scoring_profile: str,
        configuration_version_id: uuid.UUID | None = None,
    ) -> EvaluationSnapshot:
        # SELECT ... FOR UPDATE: serializes concurrent reevaluate calls
        # against this same Trade -- see TradeRepository.get_by_id_for_update's
        # own docstring for why a row lock (not an advisory lock) is the
        # right mechanism here.
        trade = await self._trades.get_by_id_for_update(trade_id)
        if trade is None or trade.user_id != user_id or trade.deleted_at is not None:
            raise NotFoundError(f"No trade with id '{trade_id}'.")

        version = await self._get_configuration_version.execute(configuration_version_id)
        if version is None:
            raise NotFoundError("No matching configuration version was found.")
        if version.status != PUBLISHED:
            raise UnprocessableEntityError(
                "Cannot reevaluate against a configuration version that is not published."
            )

        checklist_snapshot = await self._checklist_snapshots.get_by_trade_id(trade_id)
        if checklist_snapshot is None:
            raise NotFoundError(f"No trade with id '{trade_id}'.")

        evaluation_result = await self._preview_evaluation.execute(
            checklist_answers=checklist_snapshot.answers,
            scoring_profile=scoring_profile,
            configuration_version_id=version.id,
        )

        current_snapshot_id = await self._evaluation_snapshots.get_current_snapshot_id(trade_id)
        if current_snapshot_id is not None:
            await self._evaluation_snapshots.mark_not_current(current_snapshot_id)

        new_snapshot = build_evaluation_snapshot(
            trade_id=trade_id,
            configuration_version_id=version.id,
            evaluation_result=evaluation_result,
        )
        await self._evaluation_snapshots.add(new_snapshot)

        await self._dispatcher.publish(
            DomainEvent(
                event_type="TradeEvaluated",
                aggregate_type="Trade",
                aggregate_id=trade_id,
                payload={"configuration_version_id": str(version.id)},
            ),
            self._session,
        )

        return new_snapshot
