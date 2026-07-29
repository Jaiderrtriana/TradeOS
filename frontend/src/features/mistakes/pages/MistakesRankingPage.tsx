import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Badge } from "../../../components/Badge";
import { DataTable } from "../../../components/DataTable";
import { Select } from "../../../components/Select";
import { getMistakeRanking } from "../api";
import { mistakesKeys } from "../queryKeys";
import type { MistakeRankingEntry, MistakeRankingSort } from "../types";

const SORT_OPTIONS: { value: MistakeRankingSort; label: string }[] = [
  { value: "cost", label: "Cost (most costly first)" },
  { value: "-cost", label: "Cost (least costly first)" },
  { value: "-frequency", label: "Frequency (most frequent first)" },
  { value: "frequency", label: "Frequency (least frequent first)" },
];

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.7's "Mistakes Ranking" row:
 * "Frequency/cost/priority... Read-only; tagging happens from Trade
 * Detail, never from here." §11's Tables Blueprint columns: "Tag,
 * Frequency, Cost, Priority," default sort "By priority." Only the
 * table is delivered this sprint — the "Mistakes Frequency/Cost" chart
 * (§12) is deferred, same as the rest of this project's charting
 * infrastructure (Recharts, explicitly deferred in the Architecture
 * Readiness Review before Sprint 4.4).
 *
 * `sort` reorders the visible rows only — each entry's own `priority`
 * column never changes, since it represents the system's stable,
 * cost-based ranking, not the current table order (approved decision,
 * Sprint 5.2).
 */
export function MistakesRankingPage() {
  const [sort, setSort] = useState<MistakeRankingSort>("cost");

  const { data, isLoading } = useQuery({
    queryKey: mistakesKeys.ranking(sort),
    queryFn: () => getMistakeRanking(sort),
  });

  const entries = data ?? [];

  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold text-text-primary">Mistakes Ranking</h1>

      <div className="mt-4 max-w-xs">
        <p className="mb-1 text-sm text-text-secondary">Sort by</p>
        <Select
          value={sort}
          onValueChange={(value) => setSort(value as MistakeRankingSort)}
          options={SORT_OPTIONS}
          aria-label="Sort by"
        />
      </div>

      <div className="mt-6">
        {isLoading ? (
          <div className="text-sm text-text-secondary">Loading…</div>
        ) : entries.length === 0 ? (
          <p className="text-sm text-text-secondary">
            No mistakes tagged yet — tag one from a Trade&apos;s detail page.
          </p>
        ) : (
          <DataTable<MistakeRankingEntry>
            columns={[
              { key: "priority", header: "Priority", render: (entry) => `#${entry.priority}` },
              {
                key: "name",
                header: "Tag",
                render: (entry) => (
                  <div className="flex items-center gap-2">
                    <span>{entry.name}</span>
                    {!entry.is_active && <Badge label="Inactive" tone="muted" />}
                  </div>
                ),
              },
              { key: "frequency", header: "Frequency", render: (entry) => entry.frequency },
              {
                key: "cost",
                header: "Cost (R)",
                render: (entry) =>
                  entry.total_cost_r !== null ? entry.total_cost_r.toFixed(2) : "—",
              },
            ]}
            rows={entries}
            getRowKey={(entry) => entry.catalog_entry_id}
          />
        )}
      </div>
    </div>
  );
}
