"""
Cursor encoding for `GET /trades` — `TRADEOS_API_SPECIFICATION.md` §7.4:
"Request: `?limit=50&cursor=<opaque_string>`." The cursor is deliberately
opaque to the client (the contract never says what it encodes) — this
module is the one place that decides its internal shape: base64 JSON of
the keyset tuple `(entered_at, id)` `TradeRepository.list_all` filters
on. A client only ever round-trips whatever `next_cursor` it was given;
it never constructs one itself.
"""

import base64
import json
import uuid
from datetime import datetime

from app.modules.trading.infrastructure.repository import TradeListCursor
from app.platform.errors import UnprocessableEntityError


def encode_trade_cursor(entered_at: datetime, trade_id: uuid.UUID) -> str:
    payload = json.dumps({"entered_at": entered_at.isoformat(), "id": str(trade_id)})
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_trade_cursor(cursor: str) -> TradeListCursor:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8"))
        return TradeListCursor(
            entered_at=datetime.fromisoformat(payload["entered_at"]),
            id=uuid.UUID(payload["id"]),
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise UnprocessableEntityError("Invalid or corrupted pagination cursor.") from exc
