"""
Journal presentation: `POST/GET /journal-entries`, `GET/PATCH/DELETE
/journal-entries/{id}` — `TRADEOS_API_SPECIFICATION.md` §6.11. A single
unified resource, not nested under `/trades/{id}/journal` — §6.11 lists
only `/api/v1/journal-entries` routes, disambiguated by request-body/
filter fields, never by URL nesting.

`Idempotency-Key` (optional header, §3.6) is handled here for `POST
/journal-entries` only, via the same generic `app/platform/idempotency.py`
helper `POST /trades` already uses — §3.6's rule ("every POST that
creates a resource") applies identically to a brand-new
`journal_entries` row, which has no natural dedup key of its own.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.journal.application.create_journal_entry import CreateJournalEntryUseCase
from app.modules.journal.application.delete_journal_entry import DeleteJournalEntryUseCase
from app.modules.journal.application.get_journal_entry import GetJournalEntryUseCase
from app.modules.journal.application.list_journal_entries import ListJournalEntriesUseCase
from app.modules.journal.application.update_journal_entry import UpdateJournalEntryUseCase
from app.modules.journal.domain.journal_entry import JournalEntry
from app.modules.journal.infrastructure.repository import JournalEntryRepository
from app.modules.journal.presentation.pagination import (
    decode_journal_entry_cursor,
    encode_journal_entry_cursor,
)
from app.modules.journal.presentation.schemas import (
    CreateJournalEntryRequest,
    JournalEntryResponse,
    PaginatedJournalEntriesResponse,
    PaginationMeta,
    UpdateJournalEntryRequest,
)
from app.modules.trading.application.get_trade_by_id import build_get_trade_by_id_use_case
from app.platform.db.session import get_db_session
from app.platform.idempotency import (
    Claim,
    StoredResponse,
    claim_idempotency_key,
    store_idempotent_response,
)
from app.platform.errors import UnprocessableEntityError
from app.platform.security.dependencies import get_current_user_id

router = APIRouter(prefix="/journal-entries", tags=["journal"])


@router.post("", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    payload: CreateJournalEntryRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JournalEntryResponse | JSONResponse:
    claim: Claim | None = None
    if idempotency_key is not None:
        claimed = await claim_idempotency_key(
            session,
            user_id=user_id,
            idempotency_key=idempotency_key,
            endpoint="POST /journal-entries",
        )
        if isinstance(claimed, StoredResponse):
            return JSONResponse(status_code=claimed.status, content=claimed.body)
        claim = claimed

    use_case = CreateJournalEntryUseCase(
        JournalEntryRepository(session), build_get_trade_by_id_use_case(session)
    )
    entry = await use_case.execute(
        user_id,
        content=payload.content,
        trade_id=payload.trade_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    response = _journal_entry_response(entry)

    if claim is not None:
        await store_idempotent_response(
            session, claim, status=status.HTTP_201_CREATED, body=response.model_dump(mode="json")
        )

    await session.commit()
    return response


@router.get("", response_model=PaginatedJournalEntriesResponse)
async def list_journal_entries(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    trade_id: UUID | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    sort: str = "-created_at",
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> PaginatedJournalEntriesResponse:
    if sort == "-created_at":
        sort_descending = True
    elif sort == "created_at":
        sort_descending = False
    else:
        # `created_at` is the only sort field any document names for
        # Journal Entries (§7.2's general rule: default sort is the most
        # business-meaningful recency field) -- no other field is
        # invented here.
        raise UnprocessableEntityError(f"Unsupported sort field: '{sort}'.")

    decoded_cursor = decode_journal_entry_cursor(cursor) if cursor is not None else None

    use_case = ListJournalEntriesUseCase(JournalEntryRepository(session))
    # Fetches one extra row to detect `has_more` without a separate COUNT
    # query -- the extra row is trimmed below, never returned.
    entries = await use_case.execute(
        user_id,
        trade_id=trade_id,
        period_start=period_start,
        period_end=period_end,
        sort_descending=sort_descending,
        cursor=decoded_cursor,
        limit=limit + 1,
    )
    has_more = len(entries) > limit
    page = entries[:limit]

    next_cursor = (
        encode_journal_entry_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
    )

    return PaginatedJournalEntriesResponse(
        data=[_journal_entry_response(entry) for entry in page],
        pagination=PaginationMeta(next_cursor=next_cursor, has_more=has_more),
    )


@router.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_journal_entry(
    entry_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> JournalEntryResponse:
    use_case = GetJournalEntryUseCase(JournalEntryRepository(session))
    entry = await use_case.execute(entry_id, user_id)
    return _journal_entry_response(entry)


@router.patch("/{entry_id}", response_model=JournalEntryResponse)
async def update_journal_entry(
    entry_id: UUID,
    payload: UpdateJournalEntryRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> JournalEntryResponse:
    use_case = UpdateJournalEntryUseCase(JournalEntryRepository(session))
    entry = await use_case.execute(entry_id, user_id, payload.content)
    await session.commit()
    return _journal_entry_response(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    entry_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    use_case = DeleteJournalEntryUseCase(JournalEntryRepository(session))
    await use_case.execute(entry_id, user_id)
    await session.commit()


def _journal_entry_response(entry: JournalEntry) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=entry.id,
        trade_id=entry.trade_id,
        period_start=entry.period_start,
        period_end=entry.period_end,
        content=entry.content,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )
