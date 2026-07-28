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
export type TradeResult = "open" | "tp" | "sl" | "be";
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
  entry_price: number;
  stop_loss: number;
  exit_price: number | null;
  size: number;
  leverage: string;
  result: TradeResult;
  realized_pnl: number;
  mfe_price: number | null;
  mae_price: number | null;
  notes: string;
  strategy_id: string | null;
  setup_id: string | null;
  session_id: string | null;
  entry_trigger_id: string | null;
  entered_at: string;
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
}

/** `POST`/`PATCH`/`close`/`reevaluate`'s response shape. */
export interface Trade extends TradeCore {
  evaluation: EvaluationSnapshot;
}

/** `GET /trades/{id}` — `Trade` plus `checklist_answers` (§7.4: "fetched
 * only via the single-resource endpoint"). */
export interface TradeDetail extends Trade {
  checklist_answers: ChecklistAnswers;
}

/** `GET /trades` list item — every `Trade` fact except `checklist_answers`,
 * with the lighter per-engine summary shape (no breakdown rows). */
export interface TradeSummary extends TradeCore {
  evaluation: EvaluationSnapshotSummary;
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

/** `POST /trades` request body. */
export interface RegisterTradePayload {
  market: string;
  direction: Direction;
  entry_price: number;
  stop_loss: number;
  scoring_profile: string;
  exit_price?: number;
  size?: number;
  leverage?: string;
  result?: TradeResult;
  strategy_id?: string;
  setup_id?: string;
  session_id?: string;
  entry_trigger_id?: string;
  notes?: string;
  mfe_price?: number;
  mae_price?: number;
  checklist_answers?: ChecklistAnswers;
}

/** `PATCH /trades/{id}` request body — every field optional; only fields
 * actually present are applied (`exclude_unset` on the backend). Fields
 * that hold a real nullable domain value accept explicit `null` to clear
 * them; the rest are simple optional overwrites. */
export interface AmendTradePayload {
  market?: string;
  direction?: Direction;
  entry_price?: number;
  stop_loss?: number;
  size?: number;
  leverage?: string;
  notes?: string;
  strategy_id?: string | null;
  setup_id?: string | null;
  session_id?: string | null;
  entry_trigger_id?: string | null;
  mfe_price?: number | null;
  mae_price?: number | null;
}

/** `POST /trades/{id}/close` request body. */
export interface CloseTradePayload {
  result: CloseResult;
  exit_price: number;
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
