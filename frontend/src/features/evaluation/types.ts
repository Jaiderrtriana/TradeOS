/**
 * Evaluation types — mirrored field-for-field from the real backend
 * schemas (TRADEOS_API_SPECIFICATION.md §6.5, §6.6; verified directly
 * against backend/app/modules/evaluation/presentation/schemas.py and
 * backend/app/modules/configuration/presentation/schemas.py, Sprints
 * 2.1/3.2). Deliberately duplicated from `features/configuration/types.ts`
 * rather than imported — TRADEOS_FRONTEND_BLUEPRINT.md §2.4: "Cross-feature
 * reuse goes through Section 7's shared component library, never through
 * one feature importing another feature's internals directly." Evaluation
 * only needs a read-only subset of Configuration's shape (no `description`,
 * no write payloads), kept as its own contract so a future change to
 * Configuration's own types never silently ripples into this feature.
 */

export interface ScoringProfile {
  code: string;
  display_name: string;
  is_active: boolean;
}

export interface ScoringCriterion {
  id: string;
  engine_type_code: string;
  category: string | null;
  name: string;
  source_field: string;
  min_value: number;
  max_value: number;
  category_map: Record<string, number> | null;
  is_active: boolean;
}

export interface CriterionBreakdownRow {
  criterion_id: string;
  criterion_name: string;
  raw_value: string;
  normalized_value: number;
  weight: number;
  contribution: number;
}

export interface GradedEngineResult {
  score: number;
  grade: string | null;
  breakdown: CriterionBreakdownRow[];
}

export interface BiasEngineResult {
  score: number;
  breakdown: CriterionBreakdownRow[];
}

export interface EvaluationSnapshot {
  confidence: GradedEngineResult;
  quality: GradedEngineResult;
  execution: GradedEngineResult;
  market_context: GradedEngineResult;
  bias: BiasEngineResult;
}

export type ChecklistAnswers = Record<string, string | number>;

export interface PreviewEvaluationPayload {
  checklist_answers: ChecklistAnswers;
  scoring_profile: string;
}
