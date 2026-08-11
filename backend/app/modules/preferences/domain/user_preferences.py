"""
Preferences domain: UserPreferences — Generic Domain, least design effort
(TRADEOS_DOMAIN_MODEL.md §3.4, §8.12). Contains no business logic beyond
holding data — theme/language/notification_settings carry no scoring or
trading semantics.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class UserPreferences:
    user_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    theme: str = "dark"
    language: str = "es"
    notification_settings: dict[str, Any] = field(default_factory=dict)
    # IANA identifier (e.g. "America/Bogota"), never a fixed offset (Sprint
    # 4, OQ-7) — `None` means "not explicitly set", resolved by the
    # frontend as: this field -> browser-detected timezone -> UTC.
    timezone: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
