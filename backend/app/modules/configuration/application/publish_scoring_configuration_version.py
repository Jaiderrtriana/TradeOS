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

Explicitly Not Triggered: any re-evaluation of existing Trades — that is
`ReevaluateTrade` (Phase 4), a separate, explicit per-Trade action.
"""

from datetime import datetime, timezone
from uuid import UUID

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

        previously_published = await self._versions.get_published()

        version.status = PUBLISHED
        version.published_at = datetime.now(timezone.utc)
        await self._versions.update_status(version)

        if previously_published is not None:
            previously_published.status = SUPERSEDED
            await self._versions.update_status(previously_published)

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
