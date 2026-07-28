import { apiRequest } from "../../api/client";
import type { CatalogEntry } from "../../shared/catalogEntries";

/**
 * Catalogs API wrappers — TRADEOS_API_SPECIFICATION.md §6.7 (Sprint 2.2,
 * verified against backend/app/modules/configuration/presentation/
 * catalogs_router.py). The read (`listCatalogEntries`) moved to
 * `src/shared/catalogEntries.ts` (Sprint 4.4) — Trading needs it too;
 * these three writes remain Configuration's own.
 */

export function createCatalogEntry(kind: string, name: string): Promise<CatalogEntry> {
  return apiRequest<CatalogEntry>("/catalogs", { method: "POST", body: { kind, name } });
}

export function updateCatalogEntry(id: string, name: string): Promise<CatalogEntry> {
  return apiRequest<CatalogEntry>(`/catalogs/${id}`, { method: "PATCH", body: { name } });
}

export function deactivateCatalogEntry(id: string): Promise<CatalogEntry> {
  return apiRequest<CatalogEntry>(`/catalogs/${id}/deactivate`, { method: "POST" });
}
