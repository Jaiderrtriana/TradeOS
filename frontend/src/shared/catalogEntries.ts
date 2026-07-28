import { apiRequest } from "../api/client";

/**
 * `GET /catalogs?kind=` (`TRADEOS_API_SPECIFICATION.md` §6.7) — read-only,
 * promoted to `src/shared/` (Sprint 4.4): `configuration` (Catalogs
 * Management) and `trading` (Pro mode's strategy/setup/session/entry-
 * trigger pickers, and the Mistake-tag `CatalogPickerModal`) both need
 * the exact same read, unchanged. Same reasoning as
 * `scoringReferenceData.ts`. Catalog entry *writes* (create/rename/
 * deactivate, `POST`/`PATCH /catalogs/...`) remain
 * `features/configuration/catalogsApi.ts`'s own — only Trading needed
 * this one, and only for reading.
 */

export type CatalogEntryKind = "setup" | "session" | "strategy" | "entry_trigger" | "mistake_tag";

export interface CatalogEntry {
  id: string;
  kind: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const catalogEntryKeys = {
  /** Prefix shared by every `.list()` key — pass this to `invalidateQueries`
   * to invalidate every kind-scoped list at once after a write. */
  all: ["catalog-entries"] as const,
  list: (kind?: string) => ["catalog-entries", kind ?? "all"] as const,
};

export function listCatalogEntries(kind?: string): Promise<CatalogEntry[]> {
  const query = kind ? `?kind=${encodeURIComponent(kind)}` : "";
  return apiRequest<CatalogEntry[]>(`/catalogs${query}`);
}
