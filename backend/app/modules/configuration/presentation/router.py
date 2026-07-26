"""
Configuration presentation: the full Configuration Module endpoint surface
(TRADEOS_API_SPECIFICATION.md §6.6) — engine types, scoring profiles,
scoring criteria, and configuration versions. Catalogs (§6.7) is a
separate sprint (2.2), not implemented here (TRADEOS_BACKEND_BLUEPRINT.md
§3.6 notes Catalogs shares this module's schema but the Master Plan sprints
it independently).

Every endpoint requires authentication (§4.5-4.6: Configuration resources
are, today, global to the single user rather than per-user owned, but
still sit behind the same bearer-token requirement as every other endpoint
in this API — none of §6.6 is listed as "Auth Required: No").
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.domain.scoring_configuration_version import (
    ScoringConfigurationVersion,
)
from app.modules.configuration.domain.scoring_criterion import ScoringCriterion
from app.modules.configuration.application.create_draft_configuration_version import (
    CreateDraftConfigurationVersionUseCase,
)
from app.modules.configuration.application.create_scoring_criterion import (
    CreateScoringCriterionUseCase,
)
from app.modules.configuration.application.create_scoring_profile import (
    CreateScoringProfileUseCase,
)
from app.modules.configuration.application.deactivate_scoring_criterion import (
    DeactivateScoringCriterionUseCase,
)
from app.modules.configuration.application.list_configuration_versions import (
    ListScoringConfigurationVersionsUseCase,
)
from app.modules.configuration.application.list_engine_types import ListEngineTypesUseCase
from app.modules.configuration.application.list_scoring_criteria import (
    ListScoringCriteriaUseCase,
)
from app.modules.configuration.application.list_scoring_profiles import (
    ListScoringProfilesUseCase,
)
from app.modules.configuration.application.publish_scoring_configuration_version import (
    PublishScoringConfigurationVersionUseCase,
)
from app.modules.configuration.application.update_draft_weights import UpdateDraftWeightsUseCase
from app.modules.configuration.application.update_scoring_criterion import (
    UpdateScoringCriterionUseCase,
)
from app.modules.configuration.infrastructure.repository import (
    EngineTypeRepository,
    ScoringConfigurationVersionRepository,
    ScoringCriterionRepository,
    ScoringProfileRepository,
    ScoringWeightRepository,
)
from app.modules.configuration.presentation.schemas import (
    CreateScoringConfigurationVersionRequest,
    CreateScoringCriterionRequest,
    CreateScoringProfileRequest,
    EngineTypeResponse,
    ScoringConfigurationVersionResponse,
    ScoringCriterionResponse,
    ScoringProfileResponse,
    ScoringWeightResponse,
    UpdateDraftWeightRequest,
    UpdateScoringCriterionRequest,
)
from app.platform.db.session import get_db_session
from app.platform.events.dispatcher import dispatcher
from app.platform.security.dependencies import get_current_user_id

router = APIRouter(prefix="/configuration", tags=["configuration"])


@router.get("/engine-types", response_model=list[EngineTypeResponse])
async def list_engine_types(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> list[EngineTypeResponse]:
    use_case = ListEngineTypesUseCase(EngineTypeRepository(session))
    engine_types = await use_case.execute()
    return [
        EngineTypeResponse(
            code=et.code,
            display_name=et.display_name,
            is_signed=et.is_signed,
            is_active=et.is_active,
        )
        for et in engine_types
    ]


@router.get("/scoring-profiles", response_model=list[ScoringProfileResponse])
async def list_scoring_profiles(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> list[ScoringProfileResponse]:
    use_case = ListScoringProfilesUseCase(ScoringProfileRepository(session))
    profiles = await use_case.execute()
    return [
        ScoringProfileResponse(code=p.code, display_name=p.display_name, is_active=p.is_active)
        for p in profiles
    ]


@router.post(
    "/scoring-profiles", response_model=ScoringProfileResponse, status_code=status.HTTP_201_CREATED
)
async def create_scoring_profile(
    payload: CreateScoringProfileRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> ScoringProfileResponse:
    use_case = CreateScoringProfileUseCase(ScoringProfileRepository(session))
    profile = await use_case.execute(payload.code, payload.display_name)
    await session.commit()
    return ScoringProfileResponse(
        code=profile.code, display_name=profile.display_name, is_active=profile.is_active
    )


@router.get("/scoring-criteria", response_model=list[ScoringCriterionResponse])
async def list_scoring_criteria(
    engine_type: str | None = None,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> list[ScoringCriterionResponse]:
    use_case = ListScoringCriteriaUseCase(ScoringCriterionRepository(session))
    criteria = await use_case.execute(engine_type)
    return [_criterion_response(c) for c in criteria]


@router.post(
    "/scoring-criteria",
    response_model=ScoringCriterionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scoring_criterion(
    payload: CreateScoringCriterionRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> ScoringCriterionResponse:
    use_case = CreateScoringCriterionUseCase(
        ScoringCriterionRepository(session), EngineTypeRepository(session)
    )
    criterion = await use_case.execute(
        id=payload.id,
        engine_type_code=payload.engine_type_code,
        name=payload.name,
        source_field=payload.source_field,
        min_value=payload.min_value,
        max_value=payload.max_value,
        category=payload.category,
        description=payload.description,
        category_map=payload.category_map,
    )
    await session.commit()
    return _criterion_response(criterion)


@router.patch("/scoring-criteria/{criterion_id}", response_model=ScoringCriterionResponse)
async def update_scoring_criterion(
    criterion_id: str,
    payload: UpdateScoringCriterionRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> ScoringCriterionResponse:
    use_case = UpdateScoringCriterionUseCase(ScoringCriterionRepository(session))
    criterion = await use_case.execute(
        criterion_id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        min_value=payload.min_value,
        max_value=payload.max_value,
        category_map=payload.category_map,
    )
    await session.commit()
    return _criterion_response(criterion)


@router.post("/scoring-criteria/{criterion_id}/deactivate", response_model=ScoringCriterionResponse)
async def deactivate_scoring_criterion(
    criterion_id: str,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> ScoringCriterionResponse:
    use_case = DeactivateScoringCriterionUseCase(ScoringCriterionRepository(session))
    criterion = await use_case.execute(criterion_id)
    await session.commit()
    return _criterion_response(criterion)


@router.get("/versions", response_model=list[ScoringConfigurationVersionResponse])
async def list_configuration_versions(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> list[ScoringConfigurationVersionResponse]:
    use_case = ListScoringConfigurationVersionsUseCase(
        ScoringConfigurationVersionRepository(session)
    )
    versions = await use_case.execute()
    return [_version_response(v) for v in versions]


@router.post(
    "/versions",
    response_model=ScoringConfigurationVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_draft_configuration_version(
    payload: CreateScoringConfigurationVersionRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> ScoringConfigurationVersionResponse:
    use_case = CreateDraftConfigurationVersionUseCase(
        ScoringConfigurationVersionRepository(session), ScoringWeightRepository(session)
    )
    version = await use_case.execute(payload.version_label, created_by_user_id=user_id)
    await session.commit()
    return _version_response(version)


@router.post("/versions/{version_id}/weights", response_model=ScoringWeightResponse)
async def update_draft_weight(
    version_id: UUID,
    payload: UpdateDraftWeightRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> ScoringWeightResponse:
    use_case = UpdateDraftWeightsUseCase(
        ScoringConfigurationVersionRepository(session),
        ScoringWeightRepository(session),
        ScoringCriterionRepository(session),
        ScoringProfileRepository(session),
    )
    weight = await use_case.execute(
        version_id, payload.criterion_id, payload.profile_code, payload.weight, payload.is_active
    )
    await session.commit()
    return ScoringWeightResponse(
        id=weight.id,
        configuration_version_id=weight.configuration_version_id,
        criterion_id=weight.criterion_id,
        profile_code=weight.profile_code,
        weight=weight.weight,
        is_active=weight.is_active,
    )


@router.post("/versions/{version_id}/publish", response_model=ScoringConfigurationVersionResponse)
async def publish_configuration_version(
    version_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> ScoringConfigurationVersionResponse:
    use_case = PublishScoringConfigurationVersionUseCase(
        ScoringConfigurationVersionRepository(session),
        ScoringWeightRepository(session),
        ScoringCriterionRepository(session),
        dispatcher,
        session,
    )
    version = await use_case.execute(version_id)
    await session.commit()
    return _version_response(version)


def _criterion_response(criterion: ScoringCriterion) -> ScoringCriterionResponse:
    return ScoringCriterionResponse(
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
    )


def _version_response(
    version: ScoringConfigurationVersion,
) -> ScoringConfigurationVersionResponse:
    return ScoringConfigurationVersionResponse(
        id=version.id,
        version_label=version.version_label,
        status=version.status,
        published_at=version.published_at,
        created_by_user_id=version.created_by_user_id,
        created_at=version.created_at,
    )
