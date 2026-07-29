import type { ListJournalEntriesFilters } from "./types";

/**
 * Query key factory — every Journal query key goes through here, never
 * an inline array literal (Architecture Readiness Review, before Sprint
 * 4.4, applied uniformly since).
 */
export const journalKeys = {
  list: (filters: ListJournalEntriesFilters) => ["journal", "entries", "list", filters] as const,
  detail: (entryId: string) => ["journal", "entries", "detail", entryId] as const,
};
