import { apiRequest } from "../../api/client";
import type {
  DimensionStatistics,
  RollingStatistics,
  RollingWindow,
  StatisticsDimension,
  StatisticsSummary,
} from "./types";

/**
 * Statistics API wrapper — TRADEOS_API_SPECIFICATION.md §6.10. Read-only:
 * no write endpoint exists in this module. Bare JSON responses, no
 * pagination envelope on any of the three endpoints — same precedent as
 * `getMistakeRanking` (`src/features/mistakes/api.ts`).
 */
export function getStatisticsOverview(): Promise<StatisticsSummary> {
  return apiRequest<StatisticsSummary>("/statistics/overview");
}

export function getStatisticsByDimension(
  dimension: StatisticsDimension,
): Promise<DimensionStatistics[]> {
  return apiRequest<DimensionStatistics[]>(
    `/statistics/by-dimension?dimension=${encodeURIComponent(dimension)}`,
  );
}

export function getStatisticsRolling(window: RollingWindow): Promise<RollingStatistics> {
  return apiRequest<RollingStatistics>(`/statistics/rolling?window=${window}`);
}
