/**
 * Mistakes types — mirrored field-for-field from the real backend schema
 * (TRADEOS_API_SPECIFICATION.md §6.9; verified directly against
 * backend/app/modules/mistakes/presentation/schemas.py, Sprint 5.2).
 *
 * `priority` is the tag's **stable** rank by total cost ascending — it
 * never changes when `sort` reorders the returned list (approved
 * decision, Sprint 5.2: Priority represents the system's primary
 * ranking metric, not a recalculated table row index).
 */
export interface MistakeRankingEntry {
  catalog_entry_id: string;
  name: string;
  is_active: boolean;
  frequency: number;
  total_cost_r: number | null;
  priority: number;
}

export type MistakeRankingSort = "cost" | "-cost" | "frequency" | "-frequency";
