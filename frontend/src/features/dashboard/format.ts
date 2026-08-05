/**
 * Dashboard number formatting — local to this feature, same "no other
 * module needs these yet" precedent as `features/statistics/format.ts`
 * (Sprint 6.2). `win_rate` arrives as a raw 0-1 ratio (never
 * pre-multiplied by 100, `TRADEOS_API_SPECIFICATION.md` §6.10), shown
 * here as a percentage.
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
