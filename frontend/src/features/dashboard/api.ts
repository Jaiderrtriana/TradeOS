import { apiRequest } from "../../api/client";
import type { DashboardSummary } from "./types";

/**
 * Dashboard API wrapper — `TRADEOS_API_SPECIFICATION.md` §6.12.
 * Read-only, no query parameters, bare JSON object — same precedent as
 * `getStatisticsOverview` (`src/features/statistics/api.ts`).
 */
export function getDashboard(): Promise<DashboardSummary> {
  return apiRequest<DashboardSummary>("/dashboard");
}
