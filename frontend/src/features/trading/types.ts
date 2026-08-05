/**
 * Trading types — mirrored field-for-field from the real backend schemas
 * (TRADEOS_API_SPECIFICATION.md §6.4/§6.5; verified directly against
 * backend/app/modules/trading/presentation/schemas.py, Sprints 4.1-4.4).
 *
 * `EvaluationSnapshot` and its nested shapes here deliberately duplicate
 * — never import — `src/shared/evaluationPreview.ts`'s preview-response
 * shapes, even though the field names look identical: this is Trading's
 * own *persisted* snapshot (nullable `score`, per `evaluation_snapshots`'
 * nullable score columns reserved for a future sixth engine, backend
 * schemas.py's own `GradedEngineResultResponse` docstring), a genuinely
 * different read than a fresh, always-non-null preview computation.
 * Mirrors the backend's own "own DTOs per module" discipline
 * (schemas.py's module docstring) applied here on the frontend.
 *
 * `ChecklistAnswers` is **not** redefined — imported from
 * `src/shared/checklist.ts`, since `POST /trades`'s `checklist_answers`
 * and `POST /evaluation/preview`'s are the exact same wire shape.
 */

import type { ChecklistAnswers } from "../../shared/checklist";

export type Direction = "long" | "short";
/** v2.0 (Trade Entry redesign, Domain Model KDD-07): `status` is now
 * independent of `result` — a Trade's lifecycle stage. */
export type TradeStatus = "planned" | "open" | "closed";
/** v2.0: `"open"` is retired as a `result` value — `result` is `null`
 * until a Trade is `Closed`. */
export type TradeResult = "tp" | "sl" | "be";
export type CloseResult = "tp" | "sl" | "be";

export interface CriterionBreakdownRow {
  criterion_id: string;
  criterion_name: string;
  raw_value: string;
  normalized_value: number;
  weight: number;
  contribution: number;
}

export interface GradedEngineResult {
  score: number | null;
  grade: string | null;
  breakdown: CriterionBreakdownRow[];
}

export interface BiasEngineResult {
  score: number | null;
  breakdown: CriterionBreakdownRow[];
}

export interface EvaluationSnapshot {
  confidence: GradedEngineResult;
  quality: GradedEngineResult;
  execution: GradedEngineResult;
  market_context: GradedEngineResult;
  bias: BiasEngineResult;
}

export interface GradedEngineSummary {
  score: number | null;
  grade: string | null;
}

export interface BiasEngineSummary {
  score: number | null;
}

export interface EvaluationSnapshotSummary {
  confidence: GradedEngineSummary;
  quality: GradedEngineSummary;
  execution: GradedEngineSummary;
  market_context: GradedEngineSummary;
  bias: BiasEngineSummary;
}

/** `GET /trades/{id}/evaluation/history` entry — the full snapshot shape
 * plus which configuration version produced it and whether it's current. */
export interface EvaluationHistoryEntry extends EvaluationSnapshot {
  is_current: boolean;
  created_at: string;
  configuration_version_id: string;
}

/** Every Trade fact common to both the full and summary shapes. */
interface TradeCore {
  id: string;
  market: string;
  direction: Direction;
  status: TradeStatus;
  // Absent while status = planned (v2.0) — required once status is
  // open|closed (Domain Model INV-TRADE-02).
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  exit_price: number | null;
  size: number;
  margin_used: number | null;
  leverage: string;
  result: TradeResult | null;
  realized_pnl: number;
  mfe_price: number | null;
  mae_price: number | null;
  notes: string;
  strategy_id: string | null;
  setup_id: string | null;
  session_id: string | null;
  entry_trigger_id: string | null;
  entered_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
  // Computed properties (TRADEOS_DATABASE_DESIGN.md §6.9) — never stored,
  // always derived fresh by the backend.
  r_multiple: number | null;
  mfe_r: number | null;
  mae_r: number | null;
  captured_pct: number | null;
  potential_left_r: number | null;
  roi_percent: number | null;
  pnl_percent: number | null;
}

/** `POST`/`PATCH`/`close`/`open`/`reevaluate`'s response shape. `evaluation`
 * is `null` while `status = planned` — no Evaluation exists yet (Domain
 * Invariant DI-13). */
export interface Trade extends TradeCore {
  evaluation: EvaluationSnapshot | null;
}

/** `GET /trades/{id}` — `Trade` plus `checklist_answers` (§7.4: "fetched
 * only via the single-resource endpoint"). */
export interface TradeDetail extends Trade {
  checklist_answers: ChecklistAnswers;
}

/** `GET /trades` list item — every `Trade` fact except `checklist_answers`,
 * with the lighter per-engine summary shape (no breakdown rows). `evaluation`
 * is `null` while `status = planned`, same as the full `Trade` shape. */
export interface TradeSummary extends TradeCore {
  evaluation: EvaluationSnapshotSummary | null;
}

export interface PaginationMeta {
  next_cursor: string | null;
  has_more: boolean;
}

export interface PaginatedTrades {
  data: TradeSummary[];
  pagination: PaginationMeta;
}

export interface TradeMistake {
  trade_id: string;
  catalog_entry_id: string;
  created_at: string;
}

/** `POST /trades` request body. v2.0: `status` is always required and
 * explicit; `entry_price`/`stop_loss`/`entered_at`/`scoring_profile` are
 * only required once `status != planned` (enforced server-side by
 * `Trade.__post_init__`, not re-duplicated as a TS type constraint here —
 * see `schemas.ts` for the actual conditional validation). */
export interface RegisterTradePayload {
  market: string;
  direction: Direction;
  status: TradeStatus;
  scoring_profile?: string;
  entry_price?: number;
  stop_loss?: number;
  take_profit?: number;
  entered_at?: string;
  exit_price?: number;
  result?: CloseResult;
  closed_at?: string;
  realized_pnl?: number;
  size?: number;
  margin_used?: number;
  leverage?: string;
  strategy_id?: string;
  setup_id?: string;
  session_id?: string;
  entry_trigger_id?: string;
  notes?: string;
  mfe_price?: number;
  mae_price?: number;
  checklist_answers?: ChecklistAnswers;
}

/** `POST /trades/{id}/open` request body (new in v2.0) — transitions a
 * `Planned` Trade to `Open`, triggering Evaluation for the first time. */
export interface OpenTradePayload {
  entry_price: number;
  entered_at: string;
  scoring_profile: string;
  stop_loss?: number;
  take_profit?: number;
  checklist_answers?: ChecklistAnswers;
}

/** `PATCH /trades/{id}` request body — every field optional; only fields
 * actually present are applied (`exclude_unset` on the backend). Fields
 * that hold a real nullable domain value accept explicit `null` to clear
 * them; the rest are simple optional overwrites. Deliberately excludes
 * `status` — transitions only ever happen via `open`/`close`. */
export interface AmendTradePayload {
  market?: string;
  direction?: Direction;
  entry_price?: number;
  stop_loss?: number;
  take_profit?: number;
  size?: number;
  margin_used?: number;
  leverage?: string;
  notes?: string;
  strategy_id?: string | null;
  setup_id?: string | null;
  session_id?: string | null;
  entry_trigger_id?: string | null;
  mfe_price?: number | null;
  mae_price?: number | null;
}

/** `POST /trades/{id}/close` request body. v2.0: `realized_pnl`/`closed_at`
 * are now trader-supplied, required fields — never server-computed. */
export interface CloseTradePayload {
  result: CloseResult;
  exit_price: number;
  realized_pnl: number;
  closed_at: string;
  mfe_price?: number;
  mae_price?: number;
}

/** `POST /trades/{id}/reevaluate` request body. */
export interface ReevaluateTradePayload {
  scoring_profile: string;
  configuration_version_id?: string;
}

/** `POST /trades/{id}/mistakes` request body. */
export interface TagMistakePayload {
  catalog_entry_id: string;
}

export type TradesSort = "entered_at" | "-entered_at";

/** `GET /trades` query parameters. */
export interface ListTradesFilters {
  direction?: Direction;
  status?: TradeStatus;
  result?: TradeResult;
  entered_after?: string;
  entered_before?: string;
  strategy_id?: string;
  setup_id?: string;
  session_id?: string;
  entry_trigger_id?: string;
  sort?: TradesSort;
  cursor?: string;
  limit?: number;
}
