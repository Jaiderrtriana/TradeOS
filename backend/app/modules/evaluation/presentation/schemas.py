"""Evaluation presentation: Pydantic schemas matching
TRADEOS_API_SPECIFICATION.md §6.5 field-for-field."""

from uuid import UUID

from pydantic import BaseModel, Field


class PreviewEvaluationRequest(BaseModel):
    # The raw {criterion_source_field: value} map (API Specification line
    # 190, TRADEOS_DATABASE_DESIGN.md §6.10) -- any value Pydantic cannot
    # coerce to str | float (e.g. a nested object or array) already fails
    # here as a 422 VALIDATION_FAILED, satisfying §6.5's "malformed
    # checklist_answers" status code without extra Use Case logic.
    checklist_answers: dict[str, str | float] = Field(default_factory=dict)
    scoring_profile: str = Field(max_length=30)
    configuration_version_id: UUID | None = None


class CriterionBreakdownRowResponse(BaseModel):
    criterion_id: str
    criterion_name: str
    raw_value: str
    normalized_value: float
    weight: float
    contribution: float


class GradedEngineResultResponse(BaseModel):
    score: float
    grade: str | None
    breakdown: list[CriterionBreakdownRowResponse]


class BiasEngineResultResponse(BaseModel):
    score: float
    breakdown: list[CriterionBreakdownRowResponse]


class EvaluationSnapshotResponse(BaseModel):
    confidence: GradedEngineResultResponse
    quality: GradedEngineResultResponse
    execution: GradedEngineResultResponse
    market_context: GradedEngineResultResponse
    bias: BiasEngineResultResponse
