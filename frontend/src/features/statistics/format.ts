/**
 * Statistics number formatting — local to this feature (no other module
 * needs these yet, unlike `MetricCard`). `win_rate` arrives as a raw 0-1
 * ratio (never pre-multiplied by 100, `TRADEOS_API_SPECIFICATION.md`
 * §6.10 / Sprint 6.1 approved convention) -- displayed here as a
 * percentage. R-multiples/Profit Factor follow the existing `.toFixed(2)`
 * convention already used by `TradeSummaryCard`/`ScorePanel`.
 */
export function formatRatioAsPercent(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

export function formatR(value: number | null): string {
  return value === null ? "—" : value.toFixed(2);
}

export function formatPnl(value: number): string {
  return value.toFixed(2);
}

export function formatScore(value: number | null): string {
  return value === null ? "—" : value.toFixed(1);
}
