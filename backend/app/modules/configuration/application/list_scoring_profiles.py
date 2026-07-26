"""ListScoringProfilesUseCase — TRADEOS_API_SPECIFICATION.md §6.6, GET
/configuration/scoring-profiles."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.domain.scoring_profile import ScoringProfile
from app.modules.configuration.infrastructure.repository import ScoringProfileRepository


class ListScoringProfilesUseCase:
    def __init__(self, repository: ScoringProfileRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[ScoringProfile]:
        return await self._repository.list_all()


def build_list_scoring_profiles_use_case(session: AsyncSession) -> ListScoringProfilesUseCase:
    """Factory exposed for Evaluation's Application layer (Sprint 3.2) —
    used to validate an incoming `scoring_profile` against real,
    currently-defined profiles (`TRADEOS_API_SPECIFICATION.md` §6.5: `422`
    for an "unrecognized `scoring_profile`") — same cross-module pattern
    as Preferences' `build_create_default_preferences_use_case`
    (Sprint 1.2)."""
    return ListScoringProfilesUseCase(ScoringProfileRepository(session))
