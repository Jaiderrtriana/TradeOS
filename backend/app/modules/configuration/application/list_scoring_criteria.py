"""ListScoringCriteriaUseCase — TRADEOS_API_SPECIFICATION.md §6.6, GET
/configuration/scoring-criteria (filterable by `engine_type`)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.domain.scoring_criterion import ScoringCriterion
from app.modules.configuration.infrastructure.repository import ScoringCriterionRepository


class ListScoringCriteriaUseCase:
    def __init__(self, repository: ScoringCriterionRepository) -> None:
        self._repository = repository

    async def execute(self, engine_type_code: str | None = None) -> list[ScoringCriterion]:
        return await self._repository.list_all(engine_type_code)


def build_list_scoring_criteria_use_case(session: AsyncSession) -> ListScoringCriteriaUseCase:
    """Factory exposed for Evaluation's Application layer (Sprint 3.2) —
    same cross-module pattern as Preferences' `build_create_default_preferences_use_case`
    (Sprint 1.2). Called once, unfiltered, by `PreviewEvaluationUseCase`
    (grouping by engine locally) rather than once per engine, to avoid an
    N+1 query pattern."""
    return ListScoringCriteriaUseCase(ScoringCriterionRepository(session))
