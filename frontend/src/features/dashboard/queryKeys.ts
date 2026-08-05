/**
 * Query key factory — every Dashboard query key goes through here,
 * never an inline array literal (same discipline as `statisticsKeys`,
 * applied uniformly since before Sprint 4.4).
 */
export const dashboardKeys = {
  summary: () => ["dashboard", "summary"] as const,
};
