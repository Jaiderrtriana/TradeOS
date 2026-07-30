"""Playbook presentation: Pydantic schemas matching
TRADEOS_API_SPECIFICATION.md §6.8 field-for-field.

`PlaybookSetupPerformanceResponse` deliberately duplicates
`statistics.presentation.schemas.StatisticsSummaryResponse`'s field set
rather than importing it -- each module owns its own HTTP contract DTOs
(no cross-module presentation-layer import, same "own DTOs per module"
discipline already applied everywhere in this project).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreatePlaybookSetupRequest(BaseModel):
    catalog_entry_id: UUID
    entry_criteria: str = ""
    exit_criteria: str = ""
    ideal_conditions: str = ""
    risk_rules: str = ""


class UpdatePlaybookSetupRequest(BaseModel):
    """All fields optional -- `TRADEOS_API_SPECIFICATION.md` §3's general
    PATCH rule: only supplied fields change."""

    entry_criteria: str | None = None
    exit_criteria: str | None = None
    ideal_conditions: str | None = None
    risk_rules: str | None = None


class AddPlaybookSetupAttachmentRequest(BaseModel):
    file_reference: str = Field(min_length=1)
    caption: str = ""


class PlaybookSetupAttachmentResponse(BaseModel):
    id: UUID
    file_reference: str
    caption: str
    created_at: datetime


class PlaybookSetupPerformanceResponse(BaseModel):
    win_rate: float | None
    expectancy_r: float | None
    average_r: float | None
    profit_factor_r: float | None
    total_pnl: float
    average_confidence_score: float | None
    average_quality_score: float | None
    average_execution_score: float | None
    average_market_context_score: float | None
    average_bias_score: float | None


class PlaybookSetupSummaryResponse(BaseModel):
    id: UUID
    catalog_entry_id: UUID
    name: str
    entry_criteria: str
    exit_criteria: str
    ideal_conditions: str
    risk_rules: str
    status: str
    created_at: datetime
    updated_at: datetime


class PlaybookSetupDetailResponse(PlaybookSetupSummaryResponse):
    performance: PlaybookSetupPerformanceResponse
    attachments: list[PlaybookSetupAttachmentResponse]


class PaginationMeta(BaseModel):
    next_cursor: str | None
    has_more: bool


class PaginatedPlaybookSetupsResponse(BaseModel):
    data: list[PlaybookSetupSummaryResponse]
    pagination: PaginationMeta
