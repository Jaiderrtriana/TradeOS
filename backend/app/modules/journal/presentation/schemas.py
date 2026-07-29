"""Journal presentation: Pydantic schemas matching
TRADEOS_API_SPECIFICATION.md §6.11 field-for-field.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateJournalEntryRequest(BaseModel):
    content: str = Field(min_length=1)
    trade_id: UUID | None = None
    period_start: date | None = None
    period_end: date | None = None


class UpdateJournalEntryRequest(BaseModel):
    """Content only — `TRADEOS_API_SPECIFICATION.md` §6.11: the reference
    type/target is immutable after creation."""

    content: str = Field(min_length=1)


class JournalEntryResponse(BaseModel):
    id: UUID
    trade_id: UUID | None
    period_start: date | None
    period_end: date | None
    content: str
    created_at: datetime
    updated_at: datetime


class PaginationMeta(BaseModel):
    next_cursor: str | None
    has_more: bool


class PaginatedJournalEntriesResponse(BaseModel):
    """The one pagination envelope shape (§7.4), applied here to Journal
    Entries — `{"data": [...], "pagination": {"next_cursor": ..., "has_more": ...}}`."""

    data: list[JournalEntryResponse]
    pagination: PaginationMeta
