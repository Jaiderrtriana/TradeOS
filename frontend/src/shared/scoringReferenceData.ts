import { apiRequest } from "../api/client";

/**
 * `src/shared/` — the frontend's own analog of the backend's
 * `shared_kernel` (`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.2): a small,
 * deliberate exception to "own DTOs per feature, never import another
 * feature's internals" (`TRADEOS_FRONTEND_BLUEPRINT.md` §2.4), reserved
 * for shapes genuinely foundational across multiple features — not a
 * dumping ground. `Evaluation` and `Configuration` both independently
 * fetch scoring criteria/profiles; before this module existed, that was
 * two separate `useQuery` calls under two different cache keys for the
 * exact same backend data (`GET /configuration/scoring-criteria`,
 * `GET /configuration/scoring-profiles`) — found by the Architecture
 * Readiness Review before Sprint 4.4, fixed here once, reused by both
 * (and by Trading's own Trade Entry checklist, Sprint 4.4).
 *
 * `features/evaluation/` and `features/configuration/` still own
 * everything else about their own domain read/write shapes — this file
 * only holds the one pair of reads both already needed identically.
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
  description: string;
  source_field: string;
  min_value: number;
  max_value: number;
  category_map: Record<string, unknown> | null;
  is_active: boolean;
}

export const scoringReferenceKeys = {
  criteria: () => ["scoring-reference", "criteria"] as const,
  profiles: () => ["scoring-reference", "profiles"] as const,
};

export function listScoringCriteria(): Promise<ScoringCriterion[]> {
  return apiRequest<ScoringCriterion[]>("/configuration/scoring-criteria");
}

export function listScoringProfiles(): Promise<ScoringProfile[]> {
  return apiRequest<ScoringProfile[]>("/configuration/scoring-profiles");
}
