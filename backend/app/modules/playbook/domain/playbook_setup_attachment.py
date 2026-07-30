"""
Playbook domain: PlaybookSetupAttachment (`TRADEOS_DATABASE_DESIGN.md`
§6.16 -- implied by Domain Model §8.8's "example references (e.g.,
screenshots)"). `file_reference` is a URL or object-storage key supplied
by the caller -- this system never handles raw file bytes or chooses an
object storage provider this sprint (Technical Stack §6.12, Open
Question OQ-6, unresolved and explicitly excluded from the Master Plan's
blocking-questions list for Phase 7; Sprint 7.1 pre-analysis).
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PlaybookSetupAttachment:
    playbook_setup_id: uuid.UUID
    file_reference: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    caption: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
