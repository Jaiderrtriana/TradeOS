"""Trading presentation: Pydantic schemas matching
TRADEOS_API_SPECIFICATION.md §6.4 field-for-field.

`EvaluationSnapshotResponse` and its nested shapes deliberately duplicate
— never import — Evaluation's own `presentation/schemas.py` shapes.
Established "own DTOs per module" discipline (Sprint 3.3): every module
defines its own presentation shapes mirroring another module's, never
importing them, even when the shape is identical field-for-field.

v2.0 (Trade Entry redesign, Domain Model KDD-07): this layer only
enforces *shape* (types, allowed enum values) — which fields are
actually required for a given `status` (INV-TRADE-02) is a business
rule, enforced once, in `Trade.__post_init__`/`validate_status_fields`
(never duplicated here as a Pydantic cross-field validator, matching
this codebase's established DDD layering, `TRADEOS_SYSTEM_ARCHITECTURE.md`
§3.3). So every field that is only conditionally required is Optional
here, and a missing-when-required field surfaces as the domain layer's
own `UnprocessableEntityError` (422), not a Pydantic 422.
"""

from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from app.modules.trading.domain.trade import DIRECTIONS, RESULTS, STATUSES

CLOSE_RESULTS = RESULTS


class RegisterTradeRequest(BaseModel):
    market: str = Field(max_length=20)
    direction: str = Field(pattern="^(" + "|".join(DIRECTIONS) + ")$")
    # Required, no default (v2.0) — every Trade must state its lifecycle
    # stage explicitly at creation, `TRADEOS_API_SPECIFICATION.md` §6.4.
    status: str = Field(pattern="^(" + "|".join(STATUSES) + ")$")
    # Required unless status = planned (§6.4) — enforced in
    # RegisterTradeUseCase, not here (see module docstring).
    scoring_profile: str | None = Field(default=None, max_length=30)
    # Required when status = open|closed; absent while status = planned
    # (§6.4) — enforced by Trade.__post_init__, not here.
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    # tz-aware only (Sprint 4 Fase 2, OQ-7 contract) — a naive datetime here
    # would otherwise be silently interpreted as the *server's* system
    # timezone before conversion to the TIMESTAMPTZ column, not the
    # trader's actual local time. The frontend is responsible for resolving
    # the display/input timezone (Preferences -> browser -> UTC) and
    # constructing an offset-qualified ISO string before it ever reaches
    # this schema.
    entered_at: AwareDatetime | None = None
    # Required additionally when status = closed (§6.4).
    exit_price: float | None = None
    result: str | None = Field(default=None, pattern="^(" + "|".join(RESULTS) + ")$")
    closed_at: AwareDatetime | None = None
    realized_pnl: float = 0
    size: float = 0
    margin_used: float | None = None
    leverage: str = ""
    strategy_id: UUID | None = None
    setup_id: UUID | None = None
    session_id: UUID | None = None
    entry_trigger_id: UUID | None = None
    notes: str = ""
    mfe_price: float | None = None
    mae_price: float | None = None
    # Ignored while status = planned (§6.4) — a Planned Trade has no
    # Evaluation to feed yet.
    checklist_answers: dict[str, str | float] = Field(default_factory=dict)


class OpenTradeRequest(BaseModel):
    """`POST /trades/{id}/open` (§6.4, new in v2.0) — transitions a
    `Planned` Trade to `Open`, triggering Evaluation for the first time."""

    entry_price: float
    entered_at: AwareDatetime
    scoring_profile: str = Field(max_length=30)
    stop_loss: float | None = None
    take_profit: float | None = None
    checklist_answers: dict[str, str | float] = Field(default_factory=dict)


class AmendTradeRequest(BaseModel):
    """`PATCH /trades/{id}` (§6.4). Every field optional — only the ones
    actually present in the request body are applied (the router reads
    `model_dump(exclude_unset=True)`, never `model_dump()`, so an
    omitted field is left untouched and an explicit `null` on a nullable
    field like `strategy_id` still clears it).

    Deliberately excludes `status`/`result`/`exit_price`/`closed_at`
    (`OpenTrade`/`CloseTrade`'s own responsibility, see
    `application/amend_trade.py`'s docstring for the citations behind
    this split) and `checklist_answers` (`ReevaluateTrade` reloads the
    existing `ChecklistSnapshot` "unchanged" — it has no PATCH-style edit
    path)."""

    market: str | None = Field(default=None, max_length=20)
    direction: str | None = Field(default=None, pattern="^(" + "|".join(DIRECTIONS) + ")$")
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    size: float | None = None
    margin_used: float | None = None
    leverage: str | None = None
    notes: str | None = None
    strategy_id: UUID | None = None
    setup_id: UUID | None = None
    session_id: UUID | None = None
    entry_trigger_id: UUID | None = None
    mfe_price: float | None = None
    mae_price: float | None = None


class CloseTradeRequest(BaseModel):
    result: str = Field(pattern="^(" + "|".join(CLOSE_RESULTS) + ")$")
    exit_price: float
    # Both new in v2.0, both trader-supplied (never derived/computed
    # server-side) — see application/close_trade.py's docstring.
    realized_pnl: float
    closed_at: AwareDatetime
    mfe_price: float | None = None
    mae_price: float | None = None


class ReevaluateTradeRequest(BaseModel):
    # Required — same approved reasoning as RegisterTradeRequest's own
    # scoring_profile (Sprint 4.1), now applied identically here (Sprint
    # 4.2): every call into Evaluation receives the same explicit input
    # contract, never persisted, never defaulted. See CHANGELOG.md.
    scoring_profile: str = Field(max_length=30)
    configuration_version_id: UUID | None = None


class TagMistakeRequest(BaseModel):
    catalog_entry_id: UUID


class TradeMistakeResponse(BaseModel):
    """Mirrors `ScoringWeightResponse`'s own precedent for a junction/
    association resource's create response (`POST /configuration/
    versions/{id}/weights`) — the full shape of the created row, using
    whichever key fields that row actually has. `trade_mistakes` has no
    surrogate `id` (composite primary key, TRADEOS_DATABASE_DESIGN.md
    §6.14), so `trade_id`/`catalog_entry_id` are that shape's own key,
    not an invented one."""

    trade_id: UUID
    catalog_entry_id: UUID
    created_at: datetime


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
    status: str
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    exit_price: float | None
    size: float
    margin_used: float | None
    leverage: str
    result: str | None
    realized_pnl: float
    mfe_price: float | None
    mae_price: float | None
    notes: str
    strategy_id: UUID | None
    setup_id: UUID | None
    session_id: UUID | None
    entry_trigger_id: UUID | None
    entered_at: datetime | None
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
    roi_percent: float | None
    pnl_percent: float | None
    # `None` while status = planned — a Planned Trade has no Evaluation
    # yet (Domain Invariant DI-13).
    evaluation: EvaluationSnapshotResponse | None


class TradeDetailResponse(TradeResponse):
    """`GET /trades/{id}` (§6.4): "full detail of one Trade... but not its
    full historical breakdown" — reuses `TradeResponse`'s exact shape (the
    current snapshot, breakdown included) and adds only what §7.4's own
    contrast with the list view implies belongs to the single-resource
    view specifically: `checklist_answers` ("fetched only via the
    single-resource endpoint"). Deliberately a separate class from
    `TradeResponse`, not an added field on it — `TradeResponse` is
    `POST`/`PATCH`/`close`'s already-shipped response contract
    (Sprints 4.1-4.2) and stays untouched.

    `{}` while status = planned — no ChecklistSnapshot exists yet
    (Domain Invariant DI-13)."""

    checklist_answers: dict[str, str | float]


class GradedEngineSummaryResponse(BaseModel):
    """The list view's lighter per-engine shape — score/grade only, no
    breakdown rows (§7.4: `GET /trades` "omits evaluation_snapshot_
    breakdowns... to keep list responses cheap")."""

    score: float | None
    grade: str | None


class BiasEngineSummaryResponse(BaseModel):
    score: float | None


class EvaluationSnapshotSummaryResponse(BaseModel):
    confidence: GradedEngineSummaryResponse
    quality: GradedEngineSummaryResponse
    execution: GradedEngineSummaryResponse
    market_context: GradedEngineSummaryResponse
    bias: BiasEngineSummaryResponse


class TradeSummaryResponse(BaseModel):
    """`GET /trades` list item (§7.4): "a lighter shape than the full
    detail view — omits evaluation_snapshot_breakdowns and
    checklist_answers." Every other Trade fact `TradeResponse` exposes is
    still present -- only the breakdown rows and the raw checklist are
    dropped."""

    id: UUID
    market: str
    direction: str
    status: str
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    exit_price: float | None
    size: float
    margin_used: float | None
    leverage: str
    result: str | None
    realized_pnl: float
    mfe_price: float | None
    mae_price: float | None
    notes: str
    strategy_id: UUID | None
    setup_id: UUID | None
    session_id: UUID | None
    entry_trigger_id: UUID | None
    entered_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    r_multiple: float | None
    mfe_r: float | None
    mae_r: float | None
    captured_pct: float | None
    potential_left_r: float | None
    roi_percent: float | None
    pnl_percent: float | None
    evaluation: EvaluationSnapshotSummaryResponse | None


class PaginationMeta(BaseModel):
    next_cursor: str | None
    has_more: bool


class PaginatedTradesResponse(BaseModel):
    """The one pagination envelope shape (§7.4), applied here to Trades —
    `{"data": [...], "pagination": {"next_cursor": ..., "has_more": ...}}`."""

    data: list[TradeSummaryResponse]
    pagination: PaginationMeta


class EvaluationHistoryEntryResponse(EvaluationSnapshotResponse):
    """`GET /trades/{id}/evaluation/history` (§6.5): "shaped like
    Section 6.5's single-snapshot response plus `is_current` and
    `created_at`" -- and, per that same endpoint's own purpose statement,
    "each tagged with which configuration_version_id produced it.\" """

    is_current: bool
    created_at: datetime
    configuration_version_id: UUID
