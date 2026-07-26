import { apiRequest } from "../../api/client";
import type { CatalogEntry } from "./types";

/**
 * Catalogs API wrappers — TRADEOS_API_SPECIFICATION.md §6.7, all 4
 * endpoints (Sprint 2.2, verified against
 * backend/app/modules/configuration/presentation/catalogs_router.py).
 */

export function listCatalogEntries(kind?: string): Promise<CatalogEntry[]> {
  const query = kind ? `?kind=${encodeURIComponent(kind)}` : "";
  return apiRequest<CatalogEntry[]>(`/catalogs${query}`);
}

export function createCatalogEntry(kind: string, name: string): Promise<CatalogEntry> {
  return apiRequest<CatalogEntry>("/catalogs", { method: "POST", body: { kind, name } });
}

export function updateCatalogEntry(id: string, name: string): Promise<CatalogEntry> {
  return apiRequest<CatalogEntry>(`/catalogs/${id}`, { method: "PATCH", body: { name } });
}

export function deactivateCatalogEntry(id: string): Promise<CatalogEntry> {
  return apiRequest<CatalogEntry>(`/catalogs/${id}/deactivate`, { method: "POST" });
}
