"""DeactivateScoringCriterionUseCase — TRADEOS_API_SPECIFICATION.md §6.6,
POST /configuration/scoring-criteria/{id}/deactivate. Domain Invariant
DI-10: deactivate, never delete."""

from datetime import datetime, timezone

from app.modules.configuration.domain.scoring_criterion import ScoringCriterion
from app.modules.configuration.infrastructure.repository import ScoringCriterionRepository
from app.platform.errors import NotFoundError


class DeactivateScoringCriterionUseCase:
    def __init__(self, repository: ScoringCriterionRepository) -> None:
        self._repository = repository

    async def execute(self, criterion_id: str) -> ScoringCriterion:
        criterion = await self._repository.get_by_id(criterion_id)
        if criterion is None:
            raise NotFoundError(f"No scoring criterion with id '{criterion_id}'.")

        criterion.is_active = False
        criterion.updated_at = datetime.now(timezone.utc)
        await self._repository.update(criterion)
        return criterion
