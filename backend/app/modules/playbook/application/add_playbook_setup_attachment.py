"""
AddPlaybookSetupAttachmentUseCase — `TRADEOS_API_SPECIFICATION.md` §6.8,
`POST /playbook-setups/{id}/attachments`: "Add a screenshot/example
reference."

`file_reference` is a caller-supplied reference (URL or object-storage
key) -- this Use Case never touches file bytes or an object storage
provider (Open Question OQ-6, unresolved and explicitly not blocking
Phase 7, Sprint 7.1 pre-analysis). No event published -- no document
names one for attachments.
"""

import uuid

from app.modules.playbook.domain.playbook_setup_attachment import PlaybookSetupAttachment
from app.modules.playbook.infrastructure.repository import (
    PlaybookSetupAttachmentRepository,
    PlaybookSetupRepository,
)
from app.platform.errors import NotFoundError


class AddPlaybookSetupAttachmentUseCase:
    def __init__(
        self,
        playbook_setup_repository: PlaybookSetupRepository,
        attachment_repository: PlaybookSetupAttachmentRepository,
    ) -> None:
        self._playbook_setups = playbook_setup_repository
        self._attachments = attachment_repository

    async def execute(
        self, setup_id: uuid.UUID, file_reference: str, caption: str = ""
    ) -> PlaybookSetupAttachment:
        setup = await self._playbook_setups.get_by_id(setup_id)
        if setup is None:
            raise NotFoundError(f"No playbook setup with id '{setup_id}'.")

        attachment = PlaybookSetupAttachment(
            playbook_setup_id=setup_id, file_reference=file_reference, caption=caption
        )
        await self._attachments.add(attachment)
        return attachment
