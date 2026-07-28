import { Badge, type BadgeTone } from "../../../components/Badge";
import type { TradeDetail } from "../types";

const RESULT_TONE: Record<string, BadgeTone> = {
  open: "neutral",
  tp: "accent",
  sl: "muted",
  be: "neutral",
};

function field(label: string, value: string) {
  return (
    <div>
      <p className="text-xs text-text-muted">{label}</p>
      <p className="text-sm text-text-primary">{value}</p>
    </div>
  );
}

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.3/§8.3's `TradeSummaryCard`: "entry/
 * exit/size/direction/r_multiple/MFE/MAE etc." — every value read
 * directly off `GET /trades/{id}`'s response, no client-side
 * recomputation (the backend already computed `r_multiple`/`mfe_r`/
 * `mae_r`/`captured_pct`/`potential_left_r`, §6.9).
 */
export function TradeSummaryCard({ trade }: { trade: TradeDetail }) {
  return (
    <div className="rounded border border-border bg-bg-surface p-4">
      <div className="flex items-center gap-3">
        <h2 className="text-base font-semibold text-text-primary">{trade.market}</h2>
        <Badge label={trade.direction === "long" ? "Long" : "Short"} tone={trade.direction === "long" ? "accent" : "muted"} />
        <Badge label={trade.result.toUpperCase()} tone={RESULT_TONE[trade.result] ?? "neutral"} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {field("Entry Price", String(trade.entry_price))}
        {field("Exit Price", trade.exit_price !== null ? String(trade.exit_price) : "—")}
        {field("Stop Loss", String(trade.stop_loss))}
        {field("Size", String(trade.size))}
        {field("Leverage", trade.leverage || "—")}
        {field("R-Multiple", trade.r_multiple !== null ? trade.r_multiple.toFixed(2) : "—")}
        {field("MFE (R)", trade.mfe_r !== null ? trade.mfe_r.toFixed(2) : "—")}
        {field("MAE (R)", trade.mae_r !== null ? trade.mae_r.toFixed(2) : "—")}
        {field("Captured %", trade.captured_pct !== null ? `${trade.captured_pct.toFixed(1)}%` : "—")}
        {field(
          "Potential Left (R)",
          trade.potential_left_r !== null ? trade.potential_left_r.toFixed(2) : "—",
        )}
        {field("Realized P&L", String(trade.realized_pnl))}
        {field("Entered At", new Date(trade.entered_at).toLocaleString())}
        {field("Closed At", trade.closed_at ? new Date(trade.closed_at).toLocaleString() : "—")}
      </div>

      {trade.notes && (
        <div className="mt-4">
          <p className="text-xs text-text-muted">Notes</p>
          <p className="text-sm text-text-primary">{trade.notes}</p>
        </div>
      )}
    </div>
  );
}
