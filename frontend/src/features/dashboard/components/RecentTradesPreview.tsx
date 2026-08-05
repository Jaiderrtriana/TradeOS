import { useNavigate } from "react-router-dom";

import { Badge, type BadgeTone } from "../../../components/Badge";
import { formatR } from "../format";
import type { DashboardTrade } from "../types";

const STATUS_TONE: Record<string, BadgeTone> = {
  planned: "neutral",
  open: "accent",
  closed: "muted",
};

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.1: "a recent Trades list preview" —
 * a deliberately lighter row than `TradeSummaryCard`/the Trades List
 * table (no evaluation breakdown, no full field set): a Dashboard
 * preview row exists to be scanned at a glance, and drilling into a row
 * navigates to Trade Detail for everything else ("navigate into any
 * composed section's full page", same section).
 */
export function RecentTradesPreview({ trades }: { trades: DashboardTrade[] }) {
  const navigate = useNavigate();

  if (trades.length === 0) {
    return (
      <p className="text-sm text-text-secondary">
        No trades yet — use “+ New Trade” to log your first one.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-border rounded border border-border bg-bg-surface">
      {trades.map((trade) => (
        <li key={trade.id}>
          <button
            type="button"
            onClick={() => navigate(`/trades/${trade.id}`)}
            className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-bg-overlay"
          >
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-text-primary">{trade.market}</span>
              <Badge
                label={trade.direction === "long" ? "Long" : "Short"}
                tone={trade.direction === "long" ? "accent" : "muted"}
              />
              <Badge
                label={trade.status.toUpperCase()}
                tone={STATUS_TONE[trade.status] ?? "neutral"}
              />
            </div>
            <span className="text-sm text-text-secondary">{formatR(trade.r_multiple)} R</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
