"""Mistakes presentation: Pydantic schemas matching
TRADEOS_API_SPECIFICATION.md §6.9 field-for-field (the response shape
itself is not documented there field-by-field -- inferred from
TRADEOS_FRONTEND_BLUEPRINT.md §11's "Tag, Frequency, Cost, Priority"
columns and approved during Sprint 5.2's pre-analysis).
"""

from uuid import UUID

from pydantic import BaseModel


class MistakeRankingEntryResponse(BaseModel):
    catalog_entry_id: UUID
    name: str
    is_active: bool
    frequency: int
    total_cost_r: float | None
    priority: int
