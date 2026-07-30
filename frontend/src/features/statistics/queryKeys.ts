import type { RollingWindow, StatisticsDimension } from "./types";

/**
 * Query key factory — every Statistics query key goes through here,
 * never an inline array literal (Architecture Readiness Review, applied
 * uniformly since before Sprint 4.4).
 */
export const statisticsKeys = {
  overview: () => ["statistics", "overview"] as const,
  byDimension: (dimension: StatisticsDimension) =>
    ["statistics", "by-dimension", dimension] as const,
  rolling: (window: RollingWindow) => ["statistics", "rolling", window] as const,
};
