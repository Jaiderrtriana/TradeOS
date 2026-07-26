"""CreateScoringProfileUseCase — TRADEOS_API_SPECIFICATION.md §6.6, POST
/configuration/scoring-profiles ("adding a profile is a data change,"
TRADEOS_DATABASE_DESIGN.md §7.0)."""

from app.modules.configuration.domain.scoring_profile import ScoringProfile
from app.modules.configuration.infrastructure.repository import ScoringProfileRepository
from app.platform.errors import ConflictError


class CreateScoringProfileUseCase:
    def __init__(self, repository: ScoringProfileRepository) -> None:
        self._repository = repository

    async def execute(self, code: str, display_name: str) -> ScoringProfile:
        existing = await self._repository.get_by_code(code)
        if existing is not None:
            raise ConflictError(f"A scoring profile with code '{code}' already exists.")

        profile = ScoringProfile(code=code, display_name=display_name)
        await self._repository.add(profile)
        return profile
