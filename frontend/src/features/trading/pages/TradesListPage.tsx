import { useInfiniteQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Badge, type BadgeTone } from "../../../components/Badge";
import { VirtualizedDataTable } from "../../../components/VirtualizedDataTable";
import { listTrades } from "../api";
import { FilterBar } from "../components/FilterBar";
import { TradeEntryModal } from "../components/TradeEntryModal";
import { tradingKeys } from "../queryKeys";
import type { ListTradesFilters, TradeSummary } from "../types";

const STATUS_TONE: Record<string, BadgeTone> = {
  planned: "neutral",
  open: "accent",
  closed: "muted",
};

const RESULT_TONE: Record<string, BadgeTone> = {
  tp: "accent",
  sl: "muted",
  be: "neutral",
};

/**
 * Trades List — `TRADEOS_FRONTEND_BLUEPRINT.md` §5.2/§8.2. Columns per
 * §11: "Market, Direction, Result, Entry/Exit, R-Multiple, Confidence
 * Grade." Backed by `VirtualizedDataTable` (Architecture Readiness
 * Review, before Sprint 4.4) — the confirmed 20,000+ trade scale target
 * (§16) is exactly why this table, not the plain `DataTable`.
 *
 * Cursor pagination (`TRADEOS_API_SPECIFICATION.md` §7.4) is modeled as
 * `useInfiniteQuery` — "Load more" appends the next page's rows to the
 * already-virtualized list, matching the opaque, forward-only cursor
 * contract (never an offset, never a page number).
 */
export function TradesListPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<ListTradesFilters>({});
  const [entryModalOpen, setEntryModalOpen] = useState(false);

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } = useInfiniteQuery({
    queryKey: tradingKeys.list(filters),
    queryFn: ({ pageParam }) => listTrades({ ...filters, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.pagination.has_more ? (lastPage.pagination.next_cursor ?? undefined) : undefined,
  });

  const trades = useMemo(() => data?.pages.flatMap((page) => page.data) ?? [], [data]);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-text-primary">Trades</h1>
        <button
          type="button"
          onClick={() => setEntryModalOpen(true)}
          className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary"
        >
          + New Trade
        </button>
      </div>

      <div className="mt-4">
        <FilterBar filters={filters} onChange={setFilters} />
      </div>

      <div className="mt-6">
        {isLoading ? (
          <div className="text-sm text-text-secondary">Loading…</div>
        ) : (
          <VirtualizedDataTable<TradeSummary>
            data={trades}
            getRowId={(trade) => trade.id}
            onRowClick={(trade) => navigate(`/trades/${trade.id}`)}
            emptyState={
              <p className="text-sm text-text-secondary">
                No trades yet — use “+ New Trade” to log your first one.
              </p>
            }
            columns={[
              { accessorKey: "market", header: "Market" },
              {
                id: "direction",
                header: "Direction",
                cell: ({ row }) => (
                  <Badge
                    label={row.original.direction === "long" ? "Long" : "Short"}
                    tone={row.original.direction === "long" ? "accent" : "muted"}
                  />
                ),
              },
              {
                id: "status",
                header: "Status",
                cell: ({ row }) => (
                  <Badge
                    label={row.original.status.toUpperCase()}
                    tone={STATUS_TONE[row.original.status] ?? "neutral"}
                  />
                ),
              },
              {
                id: "result",
                header: "Result",
                cell: ({ row }) =>
                  row.original.result !== null ? (
                    <Badge
                      label={row.original.result.toUpperCase()}
                      tone={RESULT_TONE[row.original.result] ?? "neutral"}
                    />
                  ) : (
                    "—"
                  ),
              },
              {
                id: "entry_exit",
                header: "Entry / Exit",
                cell: ({ row }) =>
                  `${row.original.entry_price ?? "—"} → ${row.original.exit_price ?? "—"}`,
              },
              {
                id: "r_multiple",
                header: "R-Multiple",
                cell: ({ row }) =>
                  row.original.r_multiple !== null ? row.original.r_multiple.toFixed(2) : "—",
              },
              {
                id: "confidence_grade",
                header: "Confidence Grade",
                cell: ({ row }) => row.original.evaluation?.confidence.grade ?? "—",
              },
            ]}
          />
        )}
      </div>

      {hasNextPage && (
        <div className="mt-4">
          <button
            type="button"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
            className="rounded border border-border px-3 py-2 text-sm text-text-secondary disabled:opacity-50"
          >
            {isFetchingNextPage ? "Loading…" : "Load more"}
          </button>
        </div>
      )}

      <TradeEntryModal
        open={entryModalOpen}
        onOpenChange={setEntryModalOpen}
        onCreated={(tradeId) => navigate(`/trades/${tradeId}`)}
      />
    </div>
  );
}
