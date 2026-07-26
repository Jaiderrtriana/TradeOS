"""
UpdateScoringCriterionUseCase — TRADEOS_API_SPECIFICATION.md §6.6, PATCH
/configuration/scoring-criteria/{id}.

"Does not allow changing engine_type_code after creation — that would
silently reinterpret every historical breakdown row referencing it" — this
Use Case's signature has no `engine_type_code` parameter at all, so that
constraint is structural, not a runtime check.
"""

from datetime import datetime, timezone
from typing import Any

from app.modules.configuration.domain.scoring_criterion import ScoringCriterion
from app.modules.configuration.infrastructure.repository import ScoringCriterionRepository
from app.platform.errors import NotFoundError, UnprocessableEntityError


class UpdateScoringCriterionUseCase:
    def __init__(self, repository: ScoringCriterionRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        criterion_id: str,
        name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        category_map: dict[str, Any] | None = None,
    ) -> ScoringCriterion:
        criterion = await self._repository.get_by_id(criterion_id)
        if criterion is None:
            raise NotFoundError(f"No scoring criterion with id '{criterion_id}'.")

        if name is not None:
            criterion.name = name
        if description is not None:
            criterion.description = description
        if category is not None:
            criterion.category = category
        if min_value is not None:
            criterion.min_value = min_value
        if max_value is not None:
            criterion.max_value = max_value
        if category_map is not None:
            criterion.category_map = category_map

        if criterion.max_value < criterion.min_value:
            raise UnprocessableEntityError("max_value must be greater than or equal to min_value.")

        criterion.updated_at = datetime.now(timezone.utc)
        await self._repository.update(criterion)
        return criterion
