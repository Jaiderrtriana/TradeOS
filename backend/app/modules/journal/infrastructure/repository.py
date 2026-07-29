"""
Journal infrastructure: `JournalEntryRepository` for the `journal` schema.

`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3: never imported directly from
outside this module.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.journal.domain.journal_entry import JournalEntry
from app.modules.journal.infrastructure.models import JournalEntryModel


class JournalEntryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: JournalEntry) -> None:
        self._session.add(
            JournalEntryModel(
                id=entry.id,
                user_id=entry.user_id,
                trade_id=entry.trade_id,
                content=entry.content,
                period_start=entry.period_start,
                period_end=entry.period_end,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
                deleted_at=entry.deleted_at,
            )
        )

    async def get_by_id(self, entry_id: uuid.UUID) -> JournalEntry | None:
        result = await self._session.execute(
            select(JournalEntryModel).where(JournalEntryModel.id == entry_id)
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row is not None else None

    async def update_content(self, entry: JournalEntry) -> None:
        """Content-only overwrite -- `TRADEOS_BACKEND_BLUEPRINT.md` §4.8:
        "reference type immutable after creation." `trade_id`/
        `period_start`/`period_end` are never written here; changing what
        an entry is "about" is delete-and-recreate, not an edit
        (`TRADEOS_API_SPECIFICATION.md` §6.11)."""
        result = await self._session.execute(
            select(JournalEntryModel).where(JournalEntryModel.id == entry.id)
        )
        row = result.scalar_one()
        row.content = entry.content
        row.updated_at = entry.updated_at

    async def soft_delete(self, entry: JournalEntry) -> None:
        result = await self._session.execute(
            select(JournalEntryModel).where(JournalEntryModel.id == entry.id)
        )
        row = result.scalar_one()
        row.deleted_at = entry.deleted_at
        row.updated_at = entry.updated_at

    async def list_all(
        self,
        *,
        user_id: uuid.UUID,
        trade_id: uuid.UUID | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
        sort_descending: bool = True,
        cursor: "JournalEntryListCursor | None" = None,
        limit: int = 50,
    ) -> list[JournalEntry]:
        """`GET /journal-entries` (`TRADEOS_API_SPECIFICATION.md` §6.11/§7).
        Keyset (never offset) pagination on `(created_at, id)` -- same
        discipline as `TradeRepository.list_all`, applied to `created_at`
        since Journal entries have no single business-meaningful "entered
        at" field of their own (§7.2's general rule: default sort is the
        most business-meaningful recency field -- for Journal, that is
        when the reflection itself was written).

        `trade_id` is an exact match. `period_start`/`period_end` filter
        by *overlap* against a period-scoped entry's own stored range
        (§6.11: "a date range overlapping period_start/period_end") --
        the standard interval-overlap test, `entry.period_start <=
        query.period_end AND entry.period_end >= query.period_start`.
        Always scoped to `user_id` and `deleted_at IS NULL`, same
        convention as every other list endpoint.
        """
        query = select(JournalEntryModel).where(
            JournalEntryModel.user_id == user_id, JournalEntryModel.deleted_at.is_(None)
        )
        if trade_id is not None:
            query = query.where(JournalEntryModel.trade_id == trade_id)
        if period_start is not None:
            query = query.where(JournalEntryModel.period_end >= period_start)
        if period_end is not None:
            query = query.where(JournalEntryModel.period_start <= period_end)

        if cursor is not None:
            if sort_descending:
                query = query.where(
                    or_(
                        JournalEntryModel.created_at < cursor.created_at,
                        and_(
                            JournalEntryModel.created_at == cursor.created_at,
                            JournalEntryModel.id < cursor.id,
                        ),
                    )
                )
            else:
                query = query.where(
                    or_(
                        JournalEntryModel.created_at > cursor.created_at,
                        and_(
                            JournalEntryModel.created_at == cursor.created_at,
                            JournalEntryModel.id > cursor.id,
                        ),
                    )
                )

        if sort_descending:
            query = query.order_by(JournalEntryModel.created_at.desc(), JournalEntryModel.id.desc())
        else:
            query = query.order_by(JournalEntryModel.created_at.asc(), JournalEntryModel.id.asc())

        query = query.limit(limit)
        result_rows = await self._session.execute(query)
        return [_to_domain(row) for row in result_rows.scalars()]


@dataclass(frozen=True)
class JournalEntryListCursor:
    """The opaque `?cursor=` value's decoded form -- see
    `journal/presentation/pagination.py` for its base64/JSON encoding."""

    created_at: datetime
    id: uuid.UUID


def _to_domain(row: JournalEntryModel) -> JournalEntry:
    return JournalEntry(
        id=row.id,
        user_id=row.user_id,
        trade_id=row.trade_id,
        content=row.content,
        period_start=row.period_start,
        period_end=row.period_end,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )
