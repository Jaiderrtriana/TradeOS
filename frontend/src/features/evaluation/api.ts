import { apiRequest } from "../../api/client";
import type {
  EvaluationSnapshot,
  PreviewEvaluationPayload,
  ScoringCriterion,
  ScoringProfile,
} from "./types";

/**
 * Evaluation API wrappers — TRADEOS_API_SPECIFICATION.md §6.5 (preview)
 * and the read-only subset of §6.6 this feature needs to build a
 * checklist form (criteria, profiles). Own copies of the Configuration
 * reads, not imports from `features/configuration/api.ts`
 * (TRADEOS_FRONTEND_BLUEPRINT.md §2.4 — no cross-feature internals).
 */

export function listScoringCriteria(): Promise<ScoringCriterion[]> {
  return apiRequest<ScoringCriterion[]>("/configuration/scoring-criteria");
}

export function listScoringProfiles(): Promise<ScoringProfile[]> {
  return apiRequest<ScoringProfile[]>("/configuration/scoring-profiles");
}

export function previewEvaluation(payload: PreviewEvaluationPayload): Promise<EvaluationSnapshot> {
  return apiRequest<EvaluationSnapshot>("/evaluation/preview", {
    method: "POST",
    body: payload,
  });
}
