/**
 * Journal types — mirrored field-for-field from the real backend schemas
 * (TRADEOS_API_SPECIFICATION.md §6.11; verified directly against
 * backend/app/modules/journal/presentation/schemas.py, Sprint 5.1).
 */

export interface JournalEntry {
  id: string;
  trade_id: string | null;
  period_start: string | null;
  period_end: string | null;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface PaginationMeta {
  next_cursor: string | null;
  has_more: boolean;
}

export interface PaginatedJournalEntries {
  data: JournalEntry[];
  pagination: PaginationMeta;
}

/** `POST /journal-entries` request body — exactly one of `trade_id` or
 * (`period_start` and `period_end`), matching the backend's own check
 * constraint (`TRADEOS_DATABASE_DESIGN.md` §6.17). */
export interface CreateJournalEntryPayload {
  content: string;
  trade_id?: string;
  period_start?: string;
  period_end?: string;
}

/** `PATCH /journal-entries/{id}` — content only; the reference type is
 * immutable after creation (`TRADEOS_API_SPECIFICATION.md` §6.11). */
export interface UpdateJournalEntryPayload {
  content: string;
}

export type JournalEntriesSort = "created_at" | "-created_at";

/** `GET /journal-entries` query parameters. */
export interface ListJournalEntriesFilters {
  trade_id?: string;
  period_start?: string;
  period_end?: string;
  sort?: JournalEntriesSort;
  cursor?: string;
  limit?: number;
}
