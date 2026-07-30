"""
Cursor encoding for `GET /playbook-setups` — same opaque-to-the-client
contract as `journal/presentation/pagination.py`: base64 JSON of the
keyset tuple `(created_at, id)` `PlaybookSetupRepository.list_all`
filters on.
"""

import base64
import json
import uuid
from datetime import datetime

from app.modules.playbook.infrastructure.repository import PlaybookSetupListCursor
from app.platform.errors import UnprocessableEntityError


def encode_playbook_setup_cursor(created_at: datetime, setup_id: uuid.UUID) -> str:
    payload = json.dumps({"created_at": created_at.isoformat(), "id": str(setup_id)})
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_playbook_setup_cursor(cursor: str) -> PlaybookSetupListCursor:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8"))
        return PlaybookSetupListCursor(
            created_at=datetime.fromisoformat(payload["created_at"]),
            id=uuid.UUID(payload["id"]),
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise UnprocessableEntityError("Invalid or corrupted pagination cursor.") from exc
