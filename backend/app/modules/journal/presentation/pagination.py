"""
Cursor encoding for `GET /journal-entries` — same opaque-to-the-client
contract as `trading/presentation/pagination.py`: base64 JSON of the
keyset tuple `(created_at, id)` `JournalEntryRepository.list_all` filters
on.
"""

import base64
import json
import uuid
from datetime import datetime

from app.modules.journal.infrastructure.repository import JournalEntryListCursor
from app.platform.errors import UnprocessableEntityError


def encode_journal_entry_cursor(created_at: datetime, entry_id: uuid.UUID) -> str:
    payload = json.dumps({"created_at": created_at.isoformat(), "id": str(entry_id)})
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_journal_entry_cursor(cursor: str) -> JournalEntryListCursor:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8"))
        return JournalEntryListCursor(
            created_at=datetime.fromisoformat(payload["created_at"]),
            id=uuid.UUID(payload["id"]),
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise UnprocessableEntityError("Invalid or corrupted pagination cursor.") from exc
