/**
 * Playbook types — mirrored field-for-field from the real backend
 * schemas (TRADEOS_API_SPECIFICATION.md §6.8; verified directly against
 * backend/app/modules/playbook/presentation/schemas.py, Sprint 7.1).
 */

export interface PlaybookSetupSummary {
  id: string;
  catalog_entry_id: string;
  name: string;
  entry_criteria: string;
  exit_criteria: string;
  ideal_conditions: string;
  risk_rules: string;
  status: "active" | "deprecated";
  created_at: string;
  updated_at: string;
}

/** Sourced exclusively from `GET /statistics/by-dimension` internally by
 * the backend — never computed or stored client-side (Sprint 7.2
 * pre-analysis: performance stays strictly read-only). */
export interface PlaybookSetupPerformance {
  win_rate: number | null;
  expectancy_r: number | null;
  average_r: number | null;
  profit_factor_r: number | null;
  total_pnl: number;
  average_confidence_score: number | null;
  average_quality_score: number | null;
  average_execution_score: number | null;
  average_market_context_score: number | null;
  average_bias_score: number | null;
}

export interface PlaybookSetupAttachment {
  id: string;
  file_reference: string;
  caption: string;
  created_at: string;
}

export interface PlaybookSetupDetail extends PlaybookSetupSummary {
  performance: PlaybookSetupPerformance;
  attachments: PlaybookSetupAttachment[];
}

export interface PaginationMeta {
  next_cursor: string | null;
  has_more: boolean;
}

export interface PaginatedPlaybookSetups {
  data: PlaybookSetupSummary[];
  pagination: PaginationMeta;
}

/** `POST /playbook-setups` — only `catalog_entry_id` is required; the
 * four text fields default to `''` server-side if omitted. */
export interface CreatePlaybookSetupPayload {
  catalog_entry_id: string;
  entry_criteria?: string;
  exit_criteria?: string;
  ideal_conditions?: string;
  risk_rules?: string;
}

/** `PATCH /playbook-setups/{id}` — genuinely partial: an omitted field
 * is left unchanged server-side. This client always sends every field
 * with its true current-or-edited value (never `undefined`) so an
 * untouched field can never be silently lost, mirroring
 * `AmendTradeModal`'s same full-current-state resend pattern. */
export interface UpdatePlaybookSetupPayload {
  entry_criteria: string;
  exit_criteria: string;
  ideal_conditions: string;
  risk_rules: string;
}

export interface AddPlaybookSetupAttachmentPayload {
  file_reference: string;
  caption?: string;
}
