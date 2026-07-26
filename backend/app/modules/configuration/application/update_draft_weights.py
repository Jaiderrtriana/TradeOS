"""
UpdateDraftWeightsUseCase — TRADEOS_BACKEND_BLUEPRINT.md §4.8;
TRADEOS_API_SPECIFICATION.md §6.6, POST /configuration/versions/{id}/weights.

"Add or update a ScoringWeight row within a draft version only... 409 if
the target version's status != draft — published versions are immutable"
(TRADEOS_DATABASE_DESIGN.md §6.6).
"""

from uuid import UUID

from app.modules.configuration.domain.scoring_configuration_version import DRAFT
from app.modules.configuration.domain.scoring_weight import ScoringWeight
from app.modules.configuration.infrastructure.repository import (
    ScoringConfigurationVersionRepository,
    ScoringCriterionRepository,
    ScoringProfileRepository,
    ScoringWeightRepository,
)
from app.platform.errors import ConflictError, NotFoundError, UnprocessableEntityError


class UpdateDraftWeightsUseCase:
    def __init__(
        self,
        version_repository: ScoringConfigurationVersionRepository,
        weight_repository: ScoringWeightRepository,
        criterion_repository: ScoringCriterionRepository,
        profile_repository: ScoringProfileRepository,
    ) -> None:
        self._versions = version_repository
        self._weights = weight_repository
        self._criteria = criterion_repository
        self._profiles = profile_repository

    async def execute(
        self,
        configuration_version_id: UUID,
        criterion_id: str,
        profile_code: str,
        weight: float,
        is_active: bool = True,
    ) -> ScoringWeight:
        version = await self._versions.get_by_id(configuration_version_id)
        if version is None:
            raise NotFoundError(f"No configuration version with id '{configuration_version_id}'.")
        if version.status != DRAFT:
            raise ConflictError("Weights can only be added or updated on a draft version.")

        if await self._criteria.get_by_id(criterion_id) is None:
            raise UnprocessableEntityError(f"No scoring criterion with id '{criterion_id}'.")
        if await self._profiles.get_by_code(profile_code) is None:
            raise UnprocessableEntityError(f"No scoring profile with code '{profile_code}'.")

        existing = await self._weights.get_by_version_criterion_profile(
            configuration_version_id, criterion_id, profile_code
        )
        if existing is not None:
            existing.weight = weight
            existing.is_active = is_active
            await self._weights.update(existing)
            return existing

        new_weight = ScoringWeight(
            configuration_version_id=configuration_version_id,
            criterion_id=criterion_id,
            profile_code=profile_code,
            weight=weight,
            is_active=is_active,
        )
        await self._weights.add(new_weight)
        return new_weight
