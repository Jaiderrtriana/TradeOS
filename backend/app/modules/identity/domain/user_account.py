"""
Identity domain: UserAccount — Generic Domain, least design effort
(TRADEOS_DOMAIN_MODEL.md §3.4, §8.11).
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class UserAccount:
    email: str
    password_hash: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
