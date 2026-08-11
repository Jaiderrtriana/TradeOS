"""
Preferences presentation: Pydantic schemas matching
TRADEOS_API_SPECIFICATION.md §6.3.

Theme/language enums: no frozen document enumerates the exact allowed
values. "dark"/"light" for theme is grounded in
TRADEOS_FRONTEND_BLUEPRINT.md §14 ("a light theme is an additive set of
values" — anticipated, even though only dark is implemented visually
today). "es"/"en" for language mirrors the two-language pattern implied by
TRADEOS_DATABASE_DESIGN.md §6.2's default ('es'). Documented as an
implementation default in CHANGELOG.md, Sprint 1.2 — not a literal spec
value.
"""

from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, field_validator

Theme = Literal["dark", "light"]
Language = Literal["es", "en"]


def _validate_iana_timezone(value: str | None) -> str | None:
    """IANA identifiers only (e.g. "America/Bogota"), never a fixed
    offset — offsets don't represent DST correctly (Sprint 4 Fase 2,
    approved contract). Validated against the real `zoneinfo` database
    rather than an allowlist, so any identifier the runtime actually
    recognizes is accepted."""
    if value is None:
        return value
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown IANA timezone identifier: {value!r}") from exc
    return value


class PreferencesResponse(BaseModel):
    theme: str
    language: str
    notification_settings: dict[str, Any]
    timezone: str | None


class UpdatePreferencesRequest(BaseModel):
    theme: Theme | None = None
    language: Language | None = None
    notification_settings: dict[str, Any] | None = None
    timezone: str | None = None

    _validate_timezone = field_validator("timezone")(_validate_iana_timezone)
