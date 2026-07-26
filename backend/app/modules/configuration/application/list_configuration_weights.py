"""
ListConfigurationWeightsUseCase — TRADEOS_API_SPECIFICATION.md §6.6, GET
/configuration/versions/{id}/weights.

Added during Sprint 2.3 as a scoped correction to Sprint 2.1: that sprint
implemented `POST .../weights` (add-or-update a single weight) but never a
read endpoint to list a version's current weights — a gap only surfaced
once the frontend's Scoring Versions page (§5.5/§8.5: "DataTable (criteria
+ their weights for this version)") needed to display them. See
CHANGELOG.md, Sprint 2.3, for the full write-up.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.domain.scoring_weight import ScoringWeight
from app.modules.configuration.infrastructure.repository import ScoringWeightRepository


class ListConfigurationWeightsUseCase:
    def __init__(self, repository: ScoringWeightRepository) -> None:
        self._repository = repository

    async def execute(self, configuration_version_id: UUID) -> list[ScoringWeight]:
        return await self._repository.list_by_version(configuration_version_id)


def build_list_configuration_weights_use_case(
    session: AsyncSession,
) -> ListConfigurationWeightsUseCase:
    """Factory exposed for Evaluation's Application layer (Sprint 3.2) —
    same cross-module pattern as Preferences' `build_create_default_preferences_use_case`
    (Sprint 1.2)."""
    return ListConfigurationWeightsUseCase(ScoringWeightRepository(session))
