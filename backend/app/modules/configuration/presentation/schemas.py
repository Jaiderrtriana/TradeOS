"""Configuration presentation: Pydantic schemas matching
TRADEOS_API_SPECIFICATION.md §6.6 field-for-field."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EngineTypeResponse(BaseModel):
    code: str
    display_name: str
    is_signed: bool
    is_active: bool


class ScoringProfileResponse(BaseModel):
    code: str
    display_name: str
    is_active: bool


class CreateScoringProfileRequest(BaseModel):
    code: str = Field(max_length=30)
    display_name: str = Field(max_length=60)


class ScoringCriterionResponse(BaseModel):
    id: str
    engine_type_code: str
    category: str | None
    name: str
    description: str
    source_field: str
    min_value: float
    max_value: float
    category_map: dict[str, Any] | None
    is_active: bool


class CreateScoringCriterionRequest(BaseModel):
    id: str = Field(max_length=64)
    engine_type_code: str = Field(max_length=30)
    name: str = Field(max_length=120)
    source_field: str = Field(max_length=64)
    min_value: float
    max_value: float
    category: str | None = Field(default=None, max_length=64)
    description: str = ""
    category_map: dict[str, Any] | None = None


class UpdateScoringCriterionRequest(BaseModel):
    # engine_type_code is deliberately absent — TRADEOS_API_SPECIFICATION.md
    # §6.6: PATCH "does not allow changing engine_type_code after creation."
    name: str | None = Field(default=None, max_length=120)
    description: str | None = None
    category: str | None = Field(default=None, max_length=64)
    min_value: float | None = None
    max_value: float | None = None
    category_map: dict[str, Any] | None = None


class ScoringConfigurationVersionResponse(BaseModel):
    id: UUID
    version_label: str
    status: str
    published_at: datetime | None
    created_by_user_id: UUID | None
    created_at: datetime


class CreateScoringConfigurationVersionRequest(BaseModel):
    version_label: str = Field(max_length=40)


class ScoringWeightResponse(BaseModel):
    id: UUID
    configuration_version_id: UUID
    criterion_id: str
    profile_code: str
    weight: float
    is_active: bool


class UpdateDraftWeightRequest(BaseModel):
    criterion_id: str = Field(max_length=64)
    profile_code: str = Field(max_length=30)
    weight: float = Field(ge=0)
    is_active: bool = True
