"""
PublishScoringConfigurationVersionUseCase — TRADEOS_BACKEND_BLUEPRINT.md
§4.4; TRADEOS_API_SPECIFICATION.md §6.6, POST
/configuration/versions/{id}/publish; illustrative flow in §11.3.

Business Flow: validate the target is a draft, and that every
ScoringCriterion referenced by an active ScoringWeight in it is itself
active -> set this version published (published_at = now()) -> set the
previously-published version (if any) superseded -> publish
ScoringConfigurationChanged. Both status flips are part of the same
transaction (the router commits once, after execute() returns) — a state
with two "published" versions or zero would itself be a Domain Invariant
violation (DI-06/DI-07).

Concurrency (`ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md`, approved):
`self._versions.lock_for_publish()` is acquired *before* reading
`get_published()`, so two concurrent `execute()` calls can never both read
the same "currently published" state and each independently decide what
to supersede — the second caller blocks until the first commits, then
reads the true, already-updated state. `ix_scoring_configuration_versions
_one_published` (migration 0006) is the structural backstop: if the
`IntegrityError` it raises is ever hit anyway (the lock was bypassed, or
two rows already violated the invariant before this fix), it is caught
below and translated to the same `ConflictError` (409) this Use Case
already returns for "already published/superseded" — a new *reason* for
an existing response shape, not a new one.

Explicitly Not Triggered: any re-evaluation of existing Trades — that is
`ReevaluateTrade` (Phase 4), a separate, explicit per-Trade action.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.domain.scoring_configuration_version import (
    DRAFT,
    PUBLISHED,
    SUPERSEDED,
    ScoringConfigurationVersion,
)
from app.modules.configuration.infrastructure.repository import (
    ScoringConfigurationVersionRepository,
    ScoringCriterionRepository,
    ScoringWeightRepository,
)
from app.platform.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.platform.events.base import DomainEvent
from app.platform.events.dispatcher import EventDispatcher


class PublishScoringConfigurationVersionUseCase:
    def __init__(
        self,
        version_repository: ScoringConfigurationVersionRepository,
        weight_repository: ScoringWeightRepository,
        criterion_repository: ScoringCriterionRepository,
        dispatcher: EventDispatcher,
        session: AsyncSession,
    ) -> None:
        self._versions = version_repository
        self._weights = weight_repository
        self._criteria = criterion_repository
        self._dispatcher = dispatcher
        self._session = session

    async def execute(self, version_id: UUID) -> ScoringConfigurationVersion:
        version = await self._versions.get_by_id(version_id)
        if version is None:
            raise NotFoundError(f"No configuration version with id '{version_id}'.")
        if version.status != DRAFT:
            raise ConflictError("Only a draft version can be published.")

        active_weights = [w for w in await self._weights.list_by_version(version_id) if w.is_active]
        # One query for every criterion, not one per weight (N+1 avoidance)
        # — a version can carry dozens of weights (Market Context alone
        # seeds 30 criteria x 3 profiles).
        active_criterion_ids = {c.id for c in await self._criteria.list_all() if c.is_active}
        for weight in active_weights:
            if weight.criterion_id not in active_criterion_ids:
                raise UnprocessableEntityError(
                    f"Cannot publish: criterion '{weight.criterion_id}' is inactive or missing."
                )

        # Must be acquired before the read below — see module docstring.
        await self._versions.lock_for_publish()
        previously_published = await self._versions.get_published()

        # Supersede the old version *before* publishing the new one — not
        # just for clarity. `ix_scoring_configuration_versions_one_published`
        # is a plain (non-deferrable) constraint, checked immediately after
        # each UPDATE, not batched at commit — publishing the new version
        # first would momentarily leave *two* rows `published` within this
        # same transaction (the old one not yet superseded), tripping the
        # constraint before this method ever reaches its own supersede
        # step. Superseding first means the row count only ever goes
        # 1 -> 0 -> 1, never 2, at every intermediate point.
        if previously_published is not None:
            previously_published.status = SUPERSEDED
            await self._versions.update_status(previously_published)

        version.status = PUBLISHED
        version.published_at = datetime.now(timezone.utc)
        await self._versions.update_status(version)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Another publish just happened. Refresh and try again.") from exc

        await self._dispatcher.publish(
            DomainEvent(
                event_type="ScoringConfigurationChanged",
                aggregate_type="ScoringConfigurationVersion",
                aggregate_id=version.id,
                payload={"version_label": version.version_label},
            ),
            self._session,
        )

        return version
