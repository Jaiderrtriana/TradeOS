import type { MistakeRankingSort } from "./types";

/**
 * Query key factory — every Mistakes query key goes through here, never
 * an inline array literal (Architecture Readiness Review, before Sprint
 * 4.4, applied uniformly since).
 */
export const mistakesKeys = {
  ranking: (sort?: MistakeRankingSort) => ["mistakes", "ranking", sort ?? "cost"] as const,
};
