import { apiRequest } from "../../api/client";
import type { EvaluationSnapshot, PreviewEvaluationPayload } from "./types";

/**
 * Evaluation API wrappers — TRADEOS_API_SPECIFICATION.md §6.5 (preview).
 * `listScoringCriteria`/`listScoringProfiles` moved to
 * `src/shared/scoringReferenceData.ts` (Architecture Readiness Review,
 * before Sprint 4.4) — Configuration's own read endpoints, fetched
 * identically by this feature and by `features/configuration/`; kept as
 * one shared read instead of two independently-cached copies of the
 * same data. See that module's own docstring for why this is a
 * deliberate exception, not a reversal, of "own DTOs per feature."
 */

export function previewEvaluation(payload: PreviewEvaluationPayload): Promise<EvaluationSnapshot> {
  return apiRequest<EvaluationSnapshot>("/evaluation/preview", {
    method: "POST",
    body: payload,
  });
}
