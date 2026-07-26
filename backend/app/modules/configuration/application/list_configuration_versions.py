"""ListScoringConfigurationVersionsUseCase — TRADEOS_API_SPECIFICATION.md
§6.6, GET /configuration/versions."""

from app.modules.configuration.domain.scoring_configuration_version import (
    ScoringConfigurationVersion,
)
from app.modules.configuration.infrastructure.repository import (
    ScoringConfigurationVersionRepository,
)


class ListScoringConfigurationVersionsUseCase:
    def __init__(self, repository: ScoringConfigurationVersionRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[ScoringConfigurationVersion]:
        return await self._repository.list_all()
