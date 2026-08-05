import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { MetricCard } from "../../../components/MetricCard";
import { TradeEntryModal } from "../../trading/components/TradeEntryModal";
import { getDashboard } from "../api";
import { RecentTradesPreview } from "../components/RecentTradesPreview";
import { TopMistakesPreview } from "../components/TopMistakesPreview";
import { formatPnl, formatR, formatRatioAsPercent } from "../format";
import { dashboardKeys } from "../queryKeys";

/**
 * Dashboard page — `TRADEOS_FRONTEND_BLUEPRINT.md` §5.1: "one-screen
 * overview, composing `GET /dashboard`... Displayed Information: exactly
 * what `GET /dashboard` returns — no additional client-side computation"
 * (Principle 1). Sprint 8.1.
 *
 * `TradeEntryModal` is imported here from the Trading feature because
 * this file lives under `features/dashboard/pages/` — this project's
 * own `eslint-plugin-boundaries` config permits a `page` to compose
 * freely across every feature (a page is "this architecture's own
 * composition point", `eslint.config.js`); every other file in this
 * feature (`api.ts`, `types.ts`, `components/*`) stays strictly isolated
 * to its own feature, same as every other module.
 */
export function DashboardPage() {
  const navigate = useNavigate();
  const [entryModalOpen, setEntryModalOpen] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: dashboardKeys.summary(),
    queryFn: getDashboard,
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-text-primary">Dashboard</h1>
        <button
          type="button"
          onClick={() => setEntryModalOpen(true)}
          className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary"
        >
          + New Trade
        </button>
      </div>

      {isLoading && <p className="mt-6 text-sm text-text-secondary">Loading…</p>}

      {isError && (
        <p className="mt-6 text-sm text-danger">
          Something went wrong loading your Dashboard. Please try again.
        </p>
      )}

      {data && (
        <>
          {data.recent_trades.length === 0 ? (
            <p className="mt-6 text-sm text-text-secondary">
              Log your first trade to see your dashboard.
            </p>
          ) : (
            <div className="mt-6 space-y-8">
              <section>
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                  <MetricCard
                    label="Win Rate"
                    value={formatRatioAsPercent(data.overview.win_rate)}
                  />
                  <MetricCard label="Expectancy (R)" value={formatR(data.overview.expectancy_r)} />
                  <MetricCard
                    label="Profit Factor"
                    value={formatR(data.overview.profit_factor_r)}
                  />
                  <MetricCard label="Average R" value={formatR(data.overview.average_r)} />
                </div>
              </section>

              <section>
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-text-primary">
                    Rolling ({data.rolling.window} trades) vs. All-Time
                  </h2>
                  <button
                    type="button"
                    onClick={() => navigate("/statistics")}
                    className="text-sm text-text-secondary hover:text-text-primary"
                  >
                    View Statistics →
                  </button>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <MetricCard
                    label="Rolling Win Rate"
                    value={formatRatioAsPercent(data.rolling.rolling.win_rate)}
                  />
                  <MetricCard
                    label="Rolling Expectancy (R)"
                    value={formatR(data.rolling.rolling.expectancy_r)}
                  />
                  <MetricCard
                    label="All-Time Win Rate"
                    value={formatRatioAsPercent(data.rolling.overall.win_rate)}
                  />
                  <MetricCard
                    label="All-Time Total P&L"
                    value={formatPnl(data.rolling.overall.total_pnl)}
                  />
                </div>
              </section>

              <section>
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-text-primary">Top Mistakes</h2>
                  <button
                    type="button"
                    onClick={() => navigate("/mistakes")}
                    className="text-sm text-text-secondary hover:text-text-primary"
                  >
                    View All →
                  </button>
                </div>
                <div className="mt-3">
                  <TopMistakesPreview mistakes={data.top_mistakes} />
                </div>
              </section>

              <section>
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-text-primary">Recent Trades</h2>
                  <button
                    type="button"
                    onClick={() => navigate("/trades")}
                    className="text-sm text-text-secondary hover:text-text-primary"
                  >
                    View All →
                  </button>
                </div>
                <div className="mt-3">
                  <RecentTradesPreview trades={data.recent_trades} />
                </div>
              </section>
            </div>
          )}
        </>
      )}

      <TradeEntryModal
        open={entryModalOpen}
        onOpenChange={setEntryModalOpen}
        onCreated={(tradeId) => navigate(`/trades/${tradeId}`)}
      />
    </div>
  );
}
