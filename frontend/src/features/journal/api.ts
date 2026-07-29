import { apiRequest } from "../../api/client";
import type {
  CreateJournalEntryPayload,
  JournalEntry,
  ListJournalEntriesFilters,
  PaginatedJournalEntries,
  UpdateJournalEntryPayload,
} from "./types";

/**
 * Journal API wrappers — TRADEOS_API_SPECIFICATION.md §6.11, every
 * endpoint shipped in Sprint 5.1 (verified against
 * backend/app/modules/journal/presentation/router.py). A single unified
 * `/journal-entries` resource — never nested under `/trades/{id}/journal`.
 */

export function createJournalEntry(payload: CreateJournalEntryPayload): Promise<JournalEntry> {
  return apiRequest<JournalEntry>("/journal-entries", { method: "POST", body: payload });
}

function buildJournalEntriesQuery(filters: ListJournalEntriesFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function listJournalEntries(
  filters: ListJournalEntriesFilters = {},
): Promise<PaginatedJournalEntries> {
  return apiRequest<PaginatedJournalEntries>(`/journal-entries${buildJournalEntriesQuery(filters)}`);
}

export function getJournalEntry(entryId: string): Promise<JournalEntry> {
  return apiRequest<JournalEntry>(`/journal-entries/${entryId}`);
}

export function updateJournalEntry(
  entryId: string,
  payload: UpdateJournalEntryPayload,
): Promise<JournalEntry> {
  return apiRequest<JournalEntry>(`/journal-entries/${entryId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function deleteJournalEntry(entryId: string): Promise<void> {
  return apiRequest<void>(`/journal-entries/${entryId}`, { method: "DELETE" });
}
