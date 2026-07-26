"""
CreateScoringCriterionUseCase — TRADEOS_BACKEND_BLUEPRINT.md §4.8;
TRADEOS_API_SPECIFICATION.md §6.6, POST /configuration/scoring-criteria.

Business Rules Applied: `max_value >= min_value`
(TRADEOS_DATABASE_DESIGN.md §6.5's check constraint, enforced here too
since Postgres CHECK constraints don't produce the API's own error
envelope shape); `engine_type_code` must reference an existing,
active EngineType.
"""

from typing import Any

from app.modules.configuration.domain.scoring_criterion import ScoringCriterion
from app.modules.configuration.infrastructure.repository import (
    EngineTypeRepository,
    ScoringCriterionRepository,
)
from app.platform.errors import ConflictError, UnprocessableEntityError


class CreateScoringCriterionUseCase:
    def __init__(
        self,
        criterion_repository: ScoringCriterionRepository,
        engine_type_repository: EngineTypeRepository,
    ) -> None:
        self._criteria = criterion_repository
        self._engine_types = engine_type_repository

    async def execute(
        self,
        id: str,
        engine_type_code: str,
        name: str,
        source_field: str,
        min_value: float,
        max_value: float,
        category: str | None = None,
        description: str = "",
        category_map: dict[str, Any] | None = None,
    ) -> ScoringCriterion:
        if max_value < min_value:
            raise UnprocessableEntityError("max_value must be greater than or equal to min_value.")

        engine_type = await self._engine_types.get_by_code(engine_type_code)
        if engine_type is None or not engine_type.is_active:
            raise UnprocessableEntityError(
                f"'{engine_type_code}' is not a known, active engine type."
            )

        existing = await self._criteria.get_by_id(id)
        if existing is not None:
            raise ConflictError(f"A scoring criterion with id '{id}' already exists.")

        criterion = ScoringCriterion(
            id=id,
            engine_type_code=engine_type_code,
            name=name,
            source_field=source_field,
            min_value=min_value,
            max_value=max_value,
            category=category,
            description=description,
            category_map=category_map,
        )
        await self._criteria.add(criterion)
        return criterion
