"""
GetConfigurationVersionUseCase — a small, new, pure-read Use Case added in
Sprint 3.2: resolves either a specific `version_id` or (when none is
supplied) the currently published version. No endpoint in
TRADEOS_API_SPECIFICATION.md §6.6 exposes a single-version lookup
directly, but `POST /evaluation/preview`'s own contract (§6.5:
"`configuration_version_id` (optional, defaults to currently published)")
needs exactly this resolution — added here, in Configuration's own
Application layer, rather than letting Evaluation reach into
Configuration's repository directly (`TRADEOS_SYSTEM_ARCHITECTURE.md`
§3.3, Forbidden Dependencies).
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.domain.scoring_configuration_version import (
    ScoringConfigurationVersion,
)
from app.modules.configuration.infrastructure.repository import (
    ScoringConfigurationVersionRepository,
)


class GetConfigurationVersionUseCase:
    def __init__(self, repository: ScoringConfigurationVersionRepository) -> None:
        self._repository = repository

    async def execute(self, version_id: UUID | None = None) -> ScoringConfigurationVersion | None:
        if version_id is not None:
            return await self._repository.get_by_id(version_id)
        return await self._repository.get_published()


def build_get_configuration_version_use_case(
    session: AsyncSession,
) -> GetConfigurationVersionUseCase:
    """Factory exposed so Evaluation's Application layer (`PreviewEvaluationUseCase`)
    can resolve a configuration version without ever importing Configuration's
    infrastructure layer directly (`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3) —
    same pattern as Preferences' `build_create_default_preferences_use_case`
    (Sprint 1.2)."""
    return GetConfigurationVersionUseCase(ScoringConfigurationVersionRepository(session))
