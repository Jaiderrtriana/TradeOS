import { apiRequest } from "../api/client";
import type { ChecklistAnswers } from "./checklist";

/**
 * `POST /evaluation/preview` (`TRADEOS_API_SPECIFICATION.md` §6.5) — one
 * HTTP contract two features call identically: Evaluation's own preview
 * page (Sprint 3.3) and Trading's Trade Entry Pro mode (Sprint 4.4,
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §6.3, "an embedded live ScoreRing
 * preview bound to POST /evaluation/preview"). Unlike Trading's own
 * *persisted* `EvaluationSnapshot` (a different backend read, over
 * different data — trading/types.ts intentionally keeps its own copy of
 * that one, mirroring the backend's "own DTOs per module" discipline),
 * this is the exact same request/response shape both features already
 * needed unchanged — promoted here rather than duplicated, same
 * reasoning as `scoringReferenceData.ts`.
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

export interface EvaluationPreviewResult {
  confidence: GradedEngineResult;
  quality: GradedEngineResult;
  execution: GradedEngineResult;
  market_context: GradedEngineResult;
  bias: BiasEngineResult;
}

export interface PreviewEvaluationPayload {
  checklist_answers: ChecklistAnswers;
  scoring_profile: string;
}

export const evaluationPreviewKeys = {
  preview: (profile: string, answers: ChecklistAnswers) =>
    ["evaluation-preview", profile, answers] as const,
};

export function previewEvaluation(
  payload: PreviewEvaluationPayload,
): Promise<EvaluationPreviewResult> {
  return apiRequest<EvaluationPreviewResult>("/evaluation/preview", {
    method: "POST",
    body: payload,
  });
}
