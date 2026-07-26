"""
Configuration infrastructure: repositories for the `configuration` schema.

TRADEOS_SYSTEM_ARCHITECTURE.md §3.3: never imported directly from outside
this module — Configuration has no other business-module dependency
(Backend Blueprint §3.5: "the most upstream context"), so unlike
Identity/Preferences no cross-module factory is needed here yet.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.domain.engine_type import EngineType
from app.modules.configuration.domain.scoring_configuration_version import (
    ScoringConfigurationVersion,
)
from app.modules.configuration.domain.scoring_criterion import ScoringCriterion
from app.modules.configuration.domain.scoring_profile import ScoringProfile
from app.modules.configuration.domain.scoring_weight import ScoringWeight
from app.modules.configuration.infrastructure.models import (
    EngineTypeModel,
    ScoringConfigurationVersionModel,
    ScoringCriterionModel,
    ScoringProfileModel,
    ScoringWeightModel,
)


class EngineTypeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[EngineType]:
        result = await self._session.execute(select(EngineTypeModel).order_by(EngineTypeModel.code))
        return [_engine_type_to_domain(row) for row in result.scalars()]

    async def get_by_code(self, code: str) -> EngineType | None:
        result = await self._session.execute(
            select(EngineTypeModel).where(EngineTypeModel.code == code)
        )
        row = result.scalar_one_or_none()
        return _engine_type_to_domain(row) if row is not None else None


class ScoringProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[ScoringProfile]:
        result = await self._session.execute(
            select(ScoringProfileModel).order_by(ScoringProfileModel.code)
        )
        return [_scoring_profile_to_domain(row) for row in result.scalars()]

    async def get_by_code(self, code: str) -> ScoringProfile | None:
        result = await self._session.execute(
            select(ScoringProfileModel).where(ScoringProfileModel.code == code)
        )
        row = result.scalar_one_or_none()
        return _scoring_profile_to_domain(row) if row is not None else None

    async def add(self, profile: ScoringProfile) -> None:
        self._session.add(
            ScoringProfileModel(
                code=profile.code,
                display_name=profile.display_name,
                is_active=profile.is_active,
                created_at=profile.created_at,
            )
        )


class ScoringCriterionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, criterion_id: str) -> ScoringCriterion | None:
        result = await self._session.execute(
            select(ScoringCriterionModel).where(ScoringCriterionModel.id == criterion_id)
        )
        row = result.scalar_one_or_none()
        return _scoring_criterion_to_domain(row) if row is not None else None

    async def list_all(self, engine_type_code: str | None = None) -> list[ScoringCriterion]:
        query = select(ScoringCriterionModel).order_by(ScoringCriterionModel.id)
        if engine_type_code is not None:
            query = query.where(ScoringCriterionModel.engine_type_code == engine_type_code)
        result = await self._session.execute(query)
        return [_scoring_criterion_to_domain(row) for row in result.scalars()]

    async def add(self, criterion: ScoringCriterion) -> None:
        self._session.add(
            ScoringCriterionModel(
                id=criterion.id,
                engine_type_code=criterion.engine_type_code,
                category=criterion.category,
                name=criterion.name,
                description=criterion.description,
                source_field=criterion.source_field,
                min_value=criterion.min_value,
                max_value=criterion.max_value,
                category_map=criterion.category_map,
                is_active=criterion.is_active,
                created_at=criterion.created_at,
                updated_at=criterion.updated_at,
            )
        )

    async def update(self, criterion: ScoringCriterion) -> None:
        result = await self._session.execute(
            select(ScoringCriterionModel).where(ScoringCriterionModel.id == criterion.id)
        )
        row = result.scalar_one()
        row.category = criterion.category
        row.name = criterion.name
        row.description = criterion.description
        row.source_field = criterion.source_field
        row.min_value = criterion.min_value
        row.max_value = criterion.max_value
        row.category_map = criterion.category_map
        row.is_active = criterion.is_active
        row.updated_at = criterion.updated_at


class ScoringConfigurationVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, version_id: uuid.UUID) -> ScoringConfigurationVersion | None:
        result = await self._session.execute(
            select(ScoringConfigurationVersionModel).where(
                ScoringConfigurationVersionModel.id == version_id
            )
        )
        row = result.scalar_one_or_none()
        return _version_to_domain(row) if row is not None else None

    async def get_published(self) -> ScoringConfigurationVersion | None:
        result = await self._session.execute(
            select(ScoringConfigurationVersionModel).where(
                ScoringConfigurationVersionModel.status == "published"
            )
        )
        row = result.scalar_one_or_none()
        return _version_to_domain(row) if row is not None else None

    async def list_all(self) -> list[ScoringConfigurationVersion]:
        result = await self._session.execute(
            select(ScoringConfigurationVersionModel).order_by(
                ScoringConfigurationVersionModel.created_at.desc()
            )
        )
        return [_version_to_domain(row) for row in result.scalars()]

    async def add(self, version: ScoringConfigurationVersion) -> None:
        self._session.add(
            ScoringConfigurationVersionModel(
                id=version.id,
                version_label=version.version_label,
                status=version.status,
                published_at=version.published_at,
                created_by_user_id=version.created_by_user_id,
                created_at=version.created_at,
            )
        )

    async def update_status(self, version: ScoringConfigurationVersion) -> None:
        result = await self._session.execute(
            select(ScoringConfigurationVersionModel).where(
                ScoringConfigurationVersionModel.id == version.id
            )
        )
        row = result.scalar_one()
        row.status = version.status
        row.published_at = version.published_at


class ScoringWeightRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_version_criterion_profile(
        self, configuration_version_id: uuid.UUID, criterion_id: str, profile_code: str
    ) -> ScoringWeight | None:
        result = await self._session.execute(
            select(ScoringWeightModel).where(
                ScoringWeightModel.configuration_version_id == configuration_version_id,
                ScoringWeightModel.criterion_id == criterion_id,
                ScoringWeightModel.profile_code == profile_code,
            )
        )
        row = result.scalar_one_or_none()
        return _scoring_weight_to_domain(row) if row is not None else None

    async def list_by_version(self, configuration_version_id: uuid.UUID) -> list[ScoringWeight]:
        result = await self._session.execute(
            select(ScoringWeightModel).where(
                ScoringWeightModel.configuration_version_id == configuration_version_id
            )
        )
        return [_scoring_weight_to_domain(row) for row in result.scalars()]

    async def add(self, weight: ScoringWeight) -> None:
        self._session.add(
            ScoringWeightModel(
                id=weight.id,
                configuration_version_id=weight.configuration_version_id,
                criterion_id=weight.criterion_id,
                profile_code=weight.profile_code,
                weight=weight.weight,
                is_active=weight.is_active,
                created_at=weight.created_at,
            )
        )

    async def update(self, weight: ScoringWeight) -> None:
        result = await self._session.execute(
            select(ScoringWeightModel).where(ScoringWeightModel.id == weight.id)
        )
        row = result.scalar_one()
        row.weight = weight.weight
        row.is_active = weight.is_active


def _engine_type_to_domain(row: EngineTypeModel) -> EngineType:
    return EngineType(
        code=row.code,
        display_name=row.display_name,
        is_signed=row.is_signed,
        is_active=row.is_active,
        created_at=row.created_at,
    )


def _scoring_profile_to_domain(row: ScoringProfileModel) -> ScoringProfile:
    return ScoringProfile(
        code=row.code,
        display_name=row.display_name,
        is_active=row.is_active,
        created_at=row.created_at,
    )


def _scoring_criterion_to_domain(row: ScoringCriterionModel) -> ScoringCriterion:
    return ScoringCriterion(
        id=row.id,
        engine_type_code=row.engine_type_code,
        name=row.name,
        source_field=row.source_field,
        min_value=float(row.min_value),
        max_value=float(row.max_value),
        category=row.category,
        description=row.description,
        category_map=row.category_map,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _version_to_domain(row: ScoringConfigurationVersionModel) -> ScoringConfigurationVersion:
    return ScoringConfigurationVersion(
        id=row.id,
        version_label=row.version_label,
        status=row.status,
        published_at=row.published_at,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at,
    )


def _scoring_weight_to_domain(row: ScoringWeightModel) -> ScoringWeight:
    return ScoringWeight(
        id=row.id,
        configuration_version_id=row.configuration_version_id,
        criterion_id=row.criterion_id,
        profile_code=row.profile_code,
        weight=float(row.weight),
        is_active=row.is_active,
        created_at=row.created_at,
    )
