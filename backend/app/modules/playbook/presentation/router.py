"""
Playbook presentation: `POST/GET /playbook-setups`, `GET/PATCH
/playbook-setups/{id}`, `POST /playbook-setups/{id}/deprecate`,
`POST /playbook-setups/{id}/attachments`,
`DELETE /playbook-setups/{id}/attachments/{attachmentId}` —
`TRADEOS_API_SPECIFICATION.md` §6.8.

No `DELETE /playbook-setups/{id}` — not in the confirmed contract
(Domain Model §13.4's lifecycle is `Active <-> Deprecated` only, no
"deleted" state reachable via any endpoint).

`Idempotency-Key` (optional header, §3.6) is handled here for the two
resource-creating `POST`s (`create_playbook_setup`, `add_attachment`),
never for `/deprecate` (an action, not a resource creation) — same
`app/platform/idempotency.py` helper `POST /journal-entries` already
uses.

No ownership scoping anywhere in this router — `PlaybookSetup` is
global, not owned by anyone specifically (`TRADEOS_API_SPECIFICATION.md`
line 101). `user_id` is still resolved (authentication remains required)
because `GET /playbook-setups/{id}` needs it to ask Statistics for *this
caller's own* trade performance.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.get_catalog_entry import build_get_catalog_entry_use_case
from app.modules.configuration.application.list_catalog_entries import (
    build_list_catalog_entries_use_case,
)
from app.modules.playbook.application.add_playbook_setup_attachment import (
    AddPlaybookSetupAttachmentUseCase,
)
from app.modules.playbook.application.create_playbook_setup import SETUP, CreatePlaybookSetupUseCase
from app.modules.playbook.application.delete_playbook_setup_attachment import (
    DeletePlaybookSetupAttachmentUseCase,
)
from app.modules.playbook.application.deprecate_playbook_setup import (
    DeprecatePlaybookSetupUseCase,
)
from app.modules.playbook.application.get_playbook_setup import (
    GetPlaybookSetupUseCase,
    PlaybookSetupDetail,
)
from app.modules.playbook.application.list_playbook_setups import ListPlaybookSetupsUseCase
from app.modules.playbook.application.update_playbook_setup import UpdatePlaybookSetupUseCase
from app.modules.playbook.domain.playbook_setup import PlaybookSetup
from app.modules.playbook.domain.playbook_setup_attachment import PlaybookSetupAttachment
from app.modules.playbook.infrastructure.repository import (
    PlaybookSetupAttachmentRepository,
    PlaybookSetupRepository,
)
from app.modules.playbook.presentation.pagination import (
    decode_playbook_setup_cursor,
    encode_playbook_setup_cursor,
)
from app.modules.playbook.presentation.schemas import (
    AddPlaybookSetupAttachmentRequest,
    CreatePlaybookSetupRequest,
    PaginatedPlaybookSetupsResponse,
    PaginationMeta,
    PlaybookSetupAttachmentResponse,
    PlaybookSetupDetailResponse,
    PlaybookSetupPerformanceResponse,
    PlaybookSetupSummaryResponse,
    UpdatePlaybookSetupRequest,
)
from app.modules.statistics.application.get_statistics_by_dimension import (
    build_get_statistics_by_dimension_use_case,
)
from app.platform.db.session import get_db_session
from app.platform.errors import UnprocessableEntityError
from app.platform.events.dispatcher import dispatcher
from app.platform.idempotency import (
    Claim,
    StoredResponse,
    claim_idempotency_key,
    store_idempotent_response,
)
from app.platform.security.dependencies import get_current_user_id

router = APIRouter(prefix="/playbook-setups", tags=["playbook"])


@router.post("", response_model=PlaybookSetupSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_playbook_setup(
    payload: CreatePlaybookSetupRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PlaybookSetupSummaryResponse | JSONResponse:
    # `user_id` is used only to scope the Idempotency-Key claim (per
    # authenticated caller) -- PlaybookSetup itself is a global resource,
    # never filtered by `user_id`.
    claim: Claim | None = None
    if idempotency_key is not None:
        claimed = await claim_idempotency_key(
            session,
            user_id=user_id,
            idempotency_key=idempotency_key,
            endpoint="POST /playbook-setups",
        )
        if isinstance(claimed, StoredResponse):
            return JSONResponse(status_code=claimed.status, content=claimed.body)
        claim = claimed

    use_case = CreatePlaybookSetupUseCase(
        PlaybookSetupRepository(session), build_get_catalog_entry_use_case(session), session
    )
    setup = await use_case.execute(
        payload.catalog_entry_id,
        entry_criteria=payload.entry_criteria,
        exit_criteria=payload.exit_criteria,
        ideal_conditions=payload.ideal_conditions,
        risk_rules=payload.risk_rules,
    )
    catalog_entry = await build_get_catalog_entry_use_case(session).execute(setup.catalog_entry_id)
    name = catalog_entry.name if catalog_entry is not None else str(setup.catalog_entry_id)
    response = _summary_response(setup, name)

    if claim is not None:
        await store_idempotent_response(
            session, claim, status=status.HTTP_201_CREATED, body=response.model_dump(mode="json")
        )

    await session.commit()
    return response


@router.get("", response_model=PaginatedPlaybookSetupsResponse)
async def list_playbook_setups(
    session: AsyncSession = Depends(get_db_session),
    sort: str = "-created_at",
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> PaginatedPlaybookSetupsResponse:
    if sort == "-created_at":
        sort_descending = True
    elif sort == "created_at":
        sort_descending = False
    else:
        # `created_at` is the only sort field any document names for
        # Playbook Setups (§7.2's general rule) -- no other field is
        # invented here.
        raise UnprocessableEntityError(f"Unsupported sort field: '{sort}'.")

    decoded_cursor = decode_playbook_setup_cursor(cursor) if cursor is not None else None

    use_case = ListPlaybookSetupsUseCase(PlaybookSetupRepository(session))
    # Fetches one extra row to detect `has_more` without a separate COUNT
    # query -- the extra row is trimmed below, never returned.
    setups = await use_case.execute(
        sort_descending=sort_descending, cursor=decoded_cursor, limit=limit + 1
    )
    has_more = len(setups) > limit
    page = setups[:limit]

    names_by_catalog_entry_id = await _resolve_names(session, page)

    next_cursor = (
        encode_playbook_setup_cursor(page[-1].created_at, page[-1].id)
        if has_more and page
        else None
    )

    return PaginatedPlaybookSetupsResponse(
        data=[
            _summary_response(setup, names_by_catalog_entry_id[setup.catalog_entry_id])
            for setup in page
        ],
        pagination=PaginationMeta(next_cursor=next_cursor, has_more=has_more),
    )


@router.get("/{setup_id}", response_model=PlaybookSetupDetailResponse)
async def get_playbook_setup(
    setup_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> PlaybookSetupDetailResponse:
    use_case = GetPlaybookSetupUseCase(
        PlaybookSetupRepository(session),
        PlaybookSetupAttachmentRepository(session),
        build_get_catalog_entry_use_case(session),
        build_get_statistics_by_dimension_use_case(session),
    )
    detail = await use_case.execute(user_id, setup_id)
    return _detail_response(detail)


@router.patch("/{setup_id}", response_model=PlaybookSetupSummaryResponse)
async def update_playbook_setup(
    setup_id: UUID,
    payload: UpdatePlaybookSetupRequest,
    session: AsyncSession = Depends(get_db_session),
) -> PlaybookSetupSummaryResponse:
    use_case = UpdatePlaybookSetupUseCase(PlaybookSetupRepository(session), dispatcher, session)
    setup = await use_case.execute(
        setup_id,
        entry_criteria=payload.entry_criteria,
        exit_criteria=payload.exit_criteria,
        ideal_conditions=payload.ideal_conditions,
        risk_rules=payload.risk_rules,
    )
    catalog_entry = await build_get_catalog_entry_use_case(session).execute(setup.catalog_entry_id)
    name = catalog_entry.name if catalog_entry is not None else str(setup.catalog_entry_id)
    response = _summary_response(setup, name)
    await session.commit()
    return response


@router.post("/{setup_id}/deprecate", response_model=PlaybookSetupSummaryResponse)
async def deprecate_playbook_setup(
    setup_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> PlaybookSetupSummaryResponse:
    use_case = DeprecatePlaybookSetupUseCase(PlaybookSetupRepository(session), dispatcher, session)
    setup = await use_case.execute(setup_id)
    catalog_entry = await build_get_catalog_entry_use_case(session).execute(setup.catalog_entry_id)
    name = catalog_entry.name if catalog_entry is not None else str(setup.catalog_entry_id)
    response = _summary_response(setup, name)
    await session.commit()
    return response


@router.post(
    "/{setup_id}/attachments",
    response_model=PlaybookSetupAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_playbook_setup_attachment(
    setup_id: UUID,
    payload: AddPlaybookSetupAttachmentRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PlaybookSetupAttachmentResponse | JSONResponse:
    # `user_id` is used only to scope the Idempotency-Key claim (per
    # authenticated caller) -- PlaybookSetup itself is a global resource,
    # never filtered by `user_id`.
    claim: Claim | None = None
    if idempotency_key is not None:
        claimed = await claim_idempotency_key(
            session,
            user_id=user_id,
            idempotency_key=idempotency_key,
            endpoint="POST /playbook-setups/{id}/attachments",
        )
        if isinstance(claimed, StoredResponse):
            return JSONResponse(status_code=claimed.status, content=claimed.body)
        claim = claimed

    use_case = AddPlaybookSetupAttachmentUseCase(
        PlaybookSetupRepository(session), PlaybookSetupAttachmentRepository(session)
    )
    attachment = await use_case.execute(setup_id, payload.file_reference, payload.caption)
    response = _attachment_response(attachment)

    if claim is not None:
        await store_idempotent_response(
            session, claim, status=status.HTTP_201_CREATED, body=response.model_dump(mode="json")
        )

    await session.commit()
    return response


@router.delete("/{setup_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playbook_setup_attachment(
    setup_id: UUID, attachment_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> None:
    use_case = DeletePlaybookSetupAttachmentUseCase(PlaybookSetupAttachmentRepository(session))
    await use_case.execute(setup_id, attachment_id)
    await session.commit()


async def _resolve_names(session: AsyncSession, setups: list[PlaybookSetup]) -> dict[UUID, str]:
    """One batched Configuration read for the whole page -- never one
    lookup per row. `catalog_entry_id` is UNIQUE per setup (the 1:1
    linkage), so a per-row lookup would always be genuine N+1, never
    deduplicated away -- `ListCatalogEntriesUseCase.execute("setup")`
    fetches every `kind=setup` entry in a single query, same pattern
    `GetStatisticsByDimensionUseCase` already uses for its own
    catalog-backed dimensions (Sprint 6.1)."""
    entries = await build_list_catalog_entries_use_case(session).execute(SETUP)
    name_by_catalog_entry_id = {entry.id: entry.name for entry in entries}
    return {
        setup.catalog_entry_id: name_by_catalog_entry_id.get(
            setup.catalog_entry_id, str(setup.catalog_entry_id)
        )
        for setup in setups
    }


def _summary_response(setup: PlaybookSetup, name: str) -> PlaybookSetupSummaryResponse:
    return PlaybookSetupSummaryResponse(
        id=setup.id,
        catalog_entry_id=setup.catalog_entry_id,
        name=name,
        entry_criteria=setup.entry_criteria,
        exit_criteria=setup.exit_criteria,
        ideal_conditions=setup.ideal_conditions,
        risk_rules=setup.risk_rules,
        status=setup.status,
        created_at=setup.created_at,
        updated_at=setup.updated_at,
    )


def _detail_response(detail: PlaybookSetupDetail) -> PlaybookSetupDetailResponse:
    summary = _summary_response(detail.setup, detail.name)
    return PlaybookSetupDetailResponse(
        **summary.model_dump(),
        performance=PlaybookSetupPerformanceResponse(
            win_rate=detail.performance.win_rate,
            expectancy_r=detail.performance.expectancy_r,
            average_r=detail.performance.average_r,
            profit_factor_r=detail.performance.profit_factor_r,
            total_pnl=detail.performance.total_pnl,
            average_confidence_score=detail.performance.average_confidence_score,
            average_quality_score=detail.performance.average_quality_score,
            average_execution_score=detail.performance.average_execution_score,
            average_market_context_score=detail.performance.average_market_context_score,
            average_bias_score=detail.performance.average_bias_score,
        ),
        attachments=[_attachment_response(a) for a in detail.attachments],
    )


def _attachment_response(attachment: PlaybookSetupAttachment) -> PlaybookSetupAttachmentResponse:
    return PlaybookSetupAttachmentResponse(
        id=attachment.id,
        file_reference=attachment.file_reference,
        caption=attachment.caption,
        created_at=attachment.created_at,
    )
