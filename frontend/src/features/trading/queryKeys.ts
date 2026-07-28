import type { ListTradesFilters } from "./types";

/**
 * Query key factory — every Trading query key goes through here, never an
 * inline array literal (Architecture Readiness Review, before Sprint 4.4).
 */
export const tradingKeys = {
  list: (filters: ListTradesFilters) => ["trading", "trades", "list", filters] as const,
  detail: (tradeId: string) => ["trading", "trades", "detail", tradeId] as const,
  evaluation: (tradeId: string) => ["trading", "trades", "evaluation", tradeId] as const,
  evaluationHistory: (tradeId: string) =>
    ["trading", "trades", "evaluation-history", tradeId] as const,
  mistakes: (tradeId: string) => ["trading", "trades", "mistakes", tradeId] as const,
};
