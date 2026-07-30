"""
DeletePlaybookSetupAttachmentUseCase — `TRADEOS_API_SPECIFICATION.md`
§6.8, `DELETE /playbook-setups/{id}/attachments/{attachmentId}`:
"Remove an attachment... hard delete is acceptable here — an attachment
is presentation content, not history."
"""

import uuid

from app.modules.playbook.infrastructure.repository import PlaybookSetupAttachmentRepository
from app.platform.errors import NotFoundError


class DeletePlaybookSetupAttachmentUseCase:
    def __init__(self, attachment_repository: PlaybookSetupAttachmentRepository) -> None:
        self._attachments = attachment_repository

    async def execute(self, setup_id: uuid.UUID, attachment_id: uuid.UUID) -> None:
        attachment = await self._attachments.get_by_id(attachment_id)
        if attachment is None or attachment.playbook_setup_id != setup_id:
            raise NotFoundError(f"No attachment with id '{attachment_id}' on this setup.")

        await self._attachments.delete(attachment)
