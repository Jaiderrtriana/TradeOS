"""ListScoringProfilesUseCase — TRADEOS_API_SPECIFICATION.md §6.6, GET
/configuration/scoring-profiles."""

from app.modules.configuration.domain.scoring_profile import ScoringProfile
from app.modules.configuration.infrastructure.repository import ScoringProfileRepository


class ListScoringProfilesUseCase:
    def __init__(self, repository: ScoringProfileRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[ScoringProfile]:
        return await self._repository.list_all()
