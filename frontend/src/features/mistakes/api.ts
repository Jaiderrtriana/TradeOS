import { apiRequest } from "../../api/client";
import type { MistakeRankingEntry, MistakeRankingSort } from "./types";

/**
 * Mistakes API wrapper — TRADEOS_API_SPECIFICATION.md §6.9. Read-only:
 * no write endpoint exists in this module (tagging happens through the
 * Trades module). A bare JSON array, no pagination envelope — same
 * precedent as `listScoringCriteria`/`listScoringProfiles`
 * (`src/shared/scoringReferenceData.ts`).
 */
export function getMistakeRanking(sort?: MistakeRankingSort): Promise<MistakeRankingEntry[]> {
  const query = sort ? `?sort=${encodeURIComponent(sort)}` : "";
  return apiRequest<MistakeRankingEntry[]>(`/mistakes/ranking${query}`);
}
