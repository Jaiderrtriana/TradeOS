"""ListScoringCriteriaUseCase — TRADEOS_API_SPECIFICATION.md §6.6, GET
/configuration/scoring-criteria (filterable by `engine_type`)."""

from app.modules.configuration.domain.scoring_criterion import ScoringCriterion
from app.modules.configuration.infrastructure.repository import ScoringCriterionRepository


class ListScoringCriteriaUseCase:
    def __init__(self, repository: ScoringCriterionRepository) -> None:
        self._repository = repository

    async def execute(self, engine_type_code: str | None = None) -> list[ScoringCriterion]:
        return await self._repository.list_all(engine_type_code)
