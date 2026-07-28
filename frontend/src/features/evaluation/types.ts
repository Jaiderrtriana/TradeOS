/**
 * Evaluation types — mirrored field-for-field from the real backend
 * schemas (TRADEOS_API_SPECIFICATION.md §6.5; verified directly against
 * backend/app/modules/evaluation/presentation/schemas.py, Sprint 3.2).
 *
 * `ScoringProfile`/`ScoringCriterion` are **not** redefined here —
 * imported from `src/shared/scoringReferenceData.ts` instead
 * (Architecture Readiness Review, before Sprint 4.4): both this feature
 * and `features/configuration/` read the exact same Configuration
 * endpoints for them, and keeping two independent copies was producing
 * two independently-cached `useQuery` results for identical data, not
 * genuine feature isolation. Every other shape below (the preview
 * response itself) is still this feature's own, per
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §2.4.
 */

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
