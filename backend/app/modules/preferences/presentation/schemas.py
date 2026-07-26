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

from pydantic import BaseModel

Theme = Literal["dark", "light"]
Language = Literal["es", "en"]


class PreferencesResponse(BaseModel):
    theme: str
    language: str
    notification_settings: dict[str, Any]


class UpdatePreferencesRequest(BaseModel):
    theme: Theme | None = None
    language: Language | None = None
    notification_settings: dict[str, Any] | None = None
