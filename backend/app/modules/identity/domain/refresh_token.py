"""
Identity domain: RefreshToken.

TRADEOS_API_SPECIFICATION.md §4.3 requires refresh tokens to be single-use
(rotation) and server-side revocable. TRADEOS_DATABASE_DESIGN.md defines no
table for this — identity.refresh_tokens (see the Sprint 1.1 migration and
CHANGELOG.md) is a necessary, approved extension of the identity schema to
satisfy that already-frozen contract; it is not a new business concept
beyond what §4.3 already specifies.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RefreshToken:
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revoked_at: datetime | None = None

    def is_valid(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return self.revoked_at is None and self.expires_at > now

    def revoke(self, now: datetime | None = None) -> None:
        self.revoked_at = now or datetime.now(timezone.utc)
