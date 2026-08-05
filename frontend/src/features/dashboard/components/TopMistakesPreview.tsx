import { formatR } from "../format";
import type { DashboardMistakeRankingEntry } from "../types";

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.1: "a Mistakes ranking preview
 * (top 3)". Read-only, same posture as the full Mistakes Ranking page —
 * tagging happens from Trade Detail, never from here.
 */
export function TopMistakesPreview({ mistakes }: { mistakes: DashboardMistakeRankingEntry[] }) {
  if (mistakes.length === 0) {
    return <p className="text-sm text-text-secondary">No mistakes tagged yet.</p>;
  }

  return (
    <ul className="divide-y divide-border rounded border border-border bg-bg-surface">
      {mistakes.map((mistake) => (
        <li
          key={mistake.catalog_entry_id}
          className="flex items-center justify-between gap-3 px-4 py-3"
        >
          <span className="text-sm text-text-primary">{mistake.name}</span>
          <span className="text-sm text-text-secondary">
            {mistake.frequency}× · {formatR(mistake.total_cost_r)} R
          </span>
        </li>
      ))}
    </ul>
  );
}
