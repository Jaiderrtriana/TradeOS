"""Trading presentation: Pydantic schemas matching
TRADEOS_API_SPECIFICATION.md §6.4 field-for-field.

`EvaluationSnapshotResponse` and its nested shapes deliberately duplicate
— never import — Evaluation's own `presentation/schemas.py` shapes.
Established "own DTOs per module" discipline (Sprint 3.3): every module
defines its own presentation shapes mirroring another module's, never
importing them, even when the shape is identical field-for-field.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.trading.domain.trade import DIRECTIONS, OPEN, RESULTS


class RegisterTradeRequest(BaseModel):
    market: str = Field(max_length=20)
    direction: str = Field(pattern="^(" + "|".join(DIRECTIONS) + ")$")
    entry_price: float
    stop_loss: float
    # Required — approved resolution, Sprint 4.1: RegisterTrade calls
    # Evaluation, which requires a scoring_profile; the original API
    # Specification omitted this field from POST /trades even though
    # POST /evaluation/preview already required it for the same
    # computation. See CHANGELOG.md.
    scoring_profile: str = Field(max_length=30)
    exit_price: float | None = None
    size: float = 0
    leverage: str = ""
    result: str = Field(default=OPEN, pattern="^(" + "|".join(RESULTS) + ")$")
    strategy_id: UUID | None = None
    setup_id: UUID | None = None
    session_id: UUID | None = None
    entry_trigger_id: UUID | None = None
    notes: str = ""
    mfe_price: float | None = None
    mae_price: float | None = None
    checklist_answers: dict[str, str | float] = Field(default_factory=dict)


class CriterionBreakdownRowResponse(BaseModel):
    criterion_id: str
    criterion_name: str
    raw_value: str
    normalized_value: float
    weight: float
    contribution: float


class GradedEngineResultResponse(BaseModel):
    # Unlike Evaluation's own preview-only schema (always a fresh, fully
    # computed score), Trading's persisted EvaluationSnapshot mirrors
    # `evaluation_snapshots`'s nullable score columns (TRADEOS_DATABASE_
    # DESIGN.md §6.11 — nullable specifically to allow a future sixth
    # engine to be added as an additive column, without back-filling
    # every historical snapshot) — so `score` is honestly optional here.
    score: float | None
    grade: str | None
    breakdown: list[CriterionBreakdownRowResponse]


class BiasEngineResultResponse(BaseModel):
    score: float | None
    breakdown: list[CriterionBreakdownRowResponse]


class EvaluationSnapshotResponse(BaseModel):
    confidence: GradedEngineResultResponse
    quality: GradedEngineResultResponse
    execution: GradedEngineResultResponse
    market_context: GradedEngineResultResponse
    bias: BiasEngineResultResponse


class TradeResponse(BaseModel):
    id: UUID
    market: str
    direction: str
    entry_price: float
    stop_loss: float
    exit_price: float | None
    size: float
    leverage: str
    result: str
    realized_pnl: float
    mfe_price: float | None
    mae_price: float | None
    notes: str
    strategy_id: UUID | None
    setup_id: UUID | None
    session_id: UUID | None
    entry_trigger_id: UUID | None
    entered_at: datetime
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Computed properties (TRADEOS_DATABASE_DESIGN.md §6.9) — never stored,
    # always derived fresh from the Trade's own facts.
    r_multiple: float | None
    mfe_r: float | None
    mae_r: float | None
    captured_pct: float | None
    potential_left_r: float | None
    evaluation: EvaluationSnapshotResponse
