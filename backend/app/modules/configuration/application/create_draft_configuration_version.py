"""
CreateDraftConfigurationVersionUseCase — TRADEOS_BACKEND_BLUEPRINT.md §4.8;
TRADEOS_API_SPECIFICATION.md §6.6, POST /configuration/versions.

"Copying forward the currently-published version's weights as a starting
point" is explicitly named as "an implementation convenience, not a
business rule this document mandates" (§6.6) — so an absent published
version (e.g., the very first version ever created) is not an error, it
simply means nothing is copied forward.
"""

import uuid

from app.modules.configuration.domain.scoring_configuration_version import (
    ScoringConfigurationVersion,
)
from app.modules.configuration.domain.scoring_weight import ScoringWeight
from app.modules.configuration.infrastructure.repository import (
    ScoringConfigurationVersionRepository,
    ScoringWeightRepository,
)
from app.platform.errors import ConflictError


class CreateDraftConfigurationVersionUseCase:
    def __init__(
        self,
        version_repository: ScoringConfigurationVersionRepository,
        weight_repository: ScoringWeightRepository,
    ) -> None:
        self._versions = version_repository
        self._weights = weight_repository

    async def execute(
        self, version_label: str, created_by_user_id: uuid.UUID | None = None
    ) -> ScoringConfigurationVersion:
        existing = await self._versions.list_all()
        if any(v.version_label == version_label for v in existing):
            raise ConflictError(
                f"A configuration version labeled '{version_label}' already exists."
            )

        draft = ScoringConfigurationVersion(
            version_label=version_label, created_by_user_id=created_by_user_id
        )
        await self._versions.add(draft)

        published = await self._versions.get_published()
        if published is not None:
            for weight in await self._weights.list_by_version(published.id):
                await self._weights.add(
                    ScoringWeight(
                        configuration_version_id=draft.id,
                        criterion_id=weight.criterion_id,
                        profile_code=weight.profile_code,
                        weight=weight.weight,
                        is_active=weight.is_active,
                    )
                )

        return draft
