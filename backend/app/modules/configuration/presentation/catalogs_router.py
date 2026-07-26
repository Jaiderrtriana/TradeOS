"""
Catalogs presentation — TRADEOS_API_SPECIFICATION.md §6.7. A second API
surface exposed from the same Configuration backend module
(TRADEOS_BACKEND_BLUEPRINT.md §3.6: "one backend module... exposing two
API surfaces"), mounted at `/catalogs` rather than `/configuration/...`.

Every endpoint requires authentication, matching Configuration's own
endpoints (§4.5-4.6: global-to-the-single-user resources, still behind the
same bearer-token requirement as everything else in this API).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.create_catalog_entry import CreateCatalogEntryUseCase
from app.modules.configuration.application.deactivate_catalog_entry import (
    DeactivateCatalogEntryUseCase,
)
from app.modules.configuration.application.list_catalog_entries import ListCatalogEntriesUseCase
from app.modules.configuration.application.update_catalog_entry import UpdateCatalogEntryUseCase
from app.modules.configuration.domain.catalog_entry import CatalogEntry
from app.modules.configuration.infrastructure.repository import CatalogEntryRepository
from app.modules.configuration.presentation.catalog_schemas import (
    CatalogEntryResponse,
    CreateCatalogEntryRequest,
    UpdateCatalogEntryRequest,
)
from app.platform.db.session import get_db_session
from app.platform.events.dispatcher import dispatcher
from app.platform.security.dependencies import get_current_user_id

router = APIRouter(prefix="/catalogs", tags=["catalogs"])


@router.get("", response_model=list[CatalogEntryResponse])
async def list_catalog_entries(
    kind: str | None = None,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> list[CatalogEntryResponse]:
    use_case = ListCatalogEntriesUseCase(CatalogEntryRepository(session))
    entries = await use_case.execute(kind)
    return [_entry_response(e) for e in entries]


@router.post("", response_model=CatalogEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_catalog_entry(
    payload: CreateCatalogEntryRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> CatalogEntryResponse:
    use_case = CreateCatalogEntryUseCase(CatalogEntryRepository(session))
    entry = await use_case.execute(payload.kind, payload.name)
    await session.commit()
    return _entry_response(entry)


@router.patch("/{entry_id}", response_model=CatalogEntryResponse)
async def update_catalog_entry(
    entry_id: UUID,
    payload: UpdateCatalogEntryRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> CatalogEntryResponse:
    use_case = UpdateCatalogEntryUseCase(CatalogEntryRepository(session))
    entry = await use_case.execute(entry_id, payload.name)
    await session.commit()
    return _entry_response(entry)


@router.post("/{entry_id}/deactivate", response_model=CatalogEntryResponse)
async def deactivate_catalog_entry(
    entry_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> CatalogEntryResponse:
    use_case = DeactivateCatalogEntryUseCase(CatalogEntryRepository(session), dispatcher, session)
    entry = await use_case.execute(entry_id)
    await session.commit()
    return _entry_response(entry)


def _entry_response(entry: CatalogEntry) -> CatalogEntryResponse:
    return CatalogEntryResponse(
        id=entry.id,
        kind=entry.kind,
        name=entry.name,
        is_active=entry.is_active,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )
