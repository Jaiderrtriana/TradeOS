"""Catalogs presentation: Pydantic schemas matching
TRADEOS_API_SPECIFICATION.md §6.7 field-for-field."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CatalogEntryResponse(BaseModel):
    id: UUID
    kind: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CreateCatalogEntryRequest(BaseModel):
    kind: str = Field(max_length=20)
    name: str = Field(max_length=120)


class UpdateCatalogEntryRequest(BaseModel):
    # kind/is_active are deliberately absent — TRADEOS_API_SPECIFICATION.md
    # §6.7: PATCH "renames or edits metadata" only; activation state is
    # POST /catalogs/{id}/deactivate's exclusive responsibility.
    name: str = Field(max_length=120)
