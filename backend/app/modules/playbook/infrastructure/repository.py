"""
Playbook infrastructure: `PlaybookSetupRepository`, `PlaybookSetupAttachmentRepository`
for the `playbook` schema.

`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3: never imported directly from
outside this module. No `user_id` filtering anywhere here -- `PlaybookSetup`
is global, not owned by anyone specifically (`TRADEOS_API_SPECIFICATION.md`
line 101, Sprint 7.1 pre-analysis), unlike every other module built so far.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.playbook.domain.playbook_setup import PlaybookSetup
from app.modules.playbook.domain.playbook_setup_attachment import PlaybookSetupAttachment
from app.modules.playbook.infrastructure.models import (
    PlaybookSetupAttachmentModel,
    PlaybookSetupModel,
)


class PlaybookSetupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, setup: PlaybookSetup) -> None:
        self._session.add(
            PlaybookSetupModel(
                id=setup.id,
                catalog_entry_id=setup.catalog_entry_id,
                entry_criteria=setup.entry_criteria,
                exit_criteria=setup.exit_criteria,
                ideal_conditions=setup.ideal_conditions,
                risk_rules=setup.risk_rules,
                status=setup.status,
                created_at=setup.created_at,
                updated_at=setup.updated_at,
                deleted_at=setup.deleted_at,
            )
        )

    async def get_by_id(self, setup_id: uuid.UUID) -> PlaybookSetup | None:
        result = await self._session.execute(
            select(PlaybookSetupModel).where(
                PlaybookSetupModel.id == setup_id, PlaybookSetupModel.deleted_at.is_(None)
            )
        )
        row = result.scalar_one_or_none()
        return _setup_to_domain(row) if row is not None else None

    async def get_by_catalog_entry_id(self, catalog_entry_id: uuid.UUID) -> PlaybookSetup | None:
        """The 1:1-linkage pre-check `CreatePlaybookSetupUseCase` uses to
        return `422` explicitly, rather than relying on the `UNIQUE`
        constraint's `IntegrityError` (`TRADEOS_API_SPECIFICATION.md`
        §6.8's literal "422 if... already linked to another Playbook
        Setup")."""
        result = await self._session.execute(
            select(PlaybookSetupModel).where(
                PlaybookSetupModel.catalog_entry_id == catalog_entry_id,
                PlaybookSetupModel.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        return _setup_to_domain(row) if row is not None else None

    async def update(self, setup: PlaybookSetup) -> None:
        result = await self._session.execute(
            select(PlaybookSetupModel).where(PlaybookSetupModel.id == setup.id)
        )
        row = result.scalar_one()
        row.entry_criteria = setup.entry_criteria
        row.exit_criteria = setup.exit_criteria
        row.ideal_conditions = setup.ideal_conditions
        row.risk_rules = setup.risk_rules
        row.status = setup.status
        row.updated_at = setup.updated_at

    async def list_all(
        self,
        *,
        sort_descending: bool = True,
        cursor: "PlaybookSetupListCursor | None" = None,
        limit: int = 50,
    ) -> list[PlaybookSetup]:
        """`GET /playbook-setups` (`TRADEOS_API_SPECIFICATION.md` §6.8/§7).
        Keyset (never offset) pagination on `(created_at, id)` -- same
        discipline as `TradeRepository.list_all`/`JournalEntryRepository.
        list_all`. No `user_id` scope (global resource)."""
        query = select(PlaybookSetupModel).where(PlaybookSetupModel.deleted_at.is_(None))

        if cursor is not None:
            if sort_descending:
                query = query.where(
                    or_(
                        PlaybookSetupModel.created_at < cursor.created_at,
                        and_(
                            PlaybookSetupModel.created_at == cursor.created_at,
                            PlaybookSetupModel.id < cursor.id,
                        ),
                    )
                )
            else:
                query = query.where(
                    or_(
                        PlaybookSetupModel.created_at > cursor.created_at,
                        and_(
                            PlaybookSetupModel.created_at == cursor.created_at,
                            PlaybookSetupModel.id > cursor.id,
                        ),
                    )
                )

        if sort_descending:
            query = query.order_by(
                PlaybookSetupModel.created_at.desc(), PlaybookSetupModel.id.desc()
            )
        else:
            query = query.order_by(PlaybookSetupModel.created_at.asc(), PlaybookSetupModel.id.asc())

        query = query.limit(limit)
        result_rows = await self._session.execute(query)
        return [_setup_to_domain(row) for row in result_rows.scalars()]


class PlaybookSetupAttachmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, attachment: PlaybookSetupAttachment) -> None:
        self._session.add(
            PlaybookSetupAttachmentModel(
                id=attachment.id,
                playbook_setup_id=attachment.playbook_setup_id,
                file_reference=attachment.file_reference,
                caption=attachment.caption,
                created_at=attachment.created_at,
            )
        )

    async def get_by_id(self, attachment_id: uuid.UUID) -> PlaybookSetupAttachment | None:
        result = await self._session.execute(
            select(PlaybookSetupAttachmentModel).where(
                PlaybookSetupAttachmentModel.id == attachment_id
            )
        )
        row = result.scalar_one_or_none()
        return _attachment_to_domain(row) if row is not None else None

    async def list_by_setup_id(self, setup_id: uuid.UUID) -> list[PlaybookSetupAttachment]:
        result = await self._session.execute(
            select(PlaybookSetupAttachmentModel)
            .where(PlaybookSetupAttachmentModel.playbook_setup_id == setup_id)
            .order_by(PlaybookSetupAttachmentModel.created_at.asc())
        )
        return [_attachment_to_domain(row) for row in result.scalars()]

    async def delete(self, attachment: PlaybookSetupAttachment) -> None:
        """Hard delete -- `TRADEOS_DATABASE_DESIGN.md` §6.16: "presentation
        content, not history"."""
        result = await self._session.execute(
            select(PlaybookSetupAttachmentModel).where(
                PlaybookSetupAttachmentModel.id == attachment.id
            )
        )
        row = result.scalar_one()
        await self._session.delete(row)


@dataclass(frozen=True)
class PlaybookSetupListCursor:
    """The opaque `?cursor=` value's decoded form -- see
    `playbook/presentation/pagination.py` for its base64/JSON encoding."""

    created_at: datetime
    id: uuid.UUID


def _setup_to_domain(row: PlaybookSetupModel) -> PlaybookSetup:
    return PlaybookSetup(
        id=row.id,
        catalog_entry_id=row.catalog_entry_id,
        entry_criteria=row.entry_criteria,
        exit_criteria=row.exit_criteria,
        ideal_conditions=row.ideal_conditions,
        risk_rules=row.risk_rules,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


def _attachment_to_domain(row: PlaybookSetupAttachmentModel) -> PlaybookSetupAttachment:
    return PlaybookSetupAttachment(
        id=row.id,
        playbook_setup_id=row.playbook_setup_id,
        file_reference=row.file_reference,
        caption=row.caption,
        created_at=row.created_at,
    )
