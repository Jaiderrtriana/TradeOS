/**
 * A plain, framework-free debounce utility — deliberately not a React
 * hook, so its timing behavior is unit-testable with Vitest's fake timers
 * alone (TRADEOS_TECHNICAL_STACK.md §10: Vitest is named for pure-logic
 * tests). Moved here from `features/evaluation/` (Sprint 4.4): Trade
 * Entry's Pro mode needs the exact same debounced-preview timing
 * `EvaluationPreviewForm` already established (Sprint 3.3) — promoted to
 * `src/shared/` rather than duplicated, same reasoning as
 * `scoringReferenceData.ts`.
 */
export interface Debouncer<Args extends unknown[]> {
  (...args: Args): void;
  cancel: () => void;
}

export function debounce<Args extends unknown[]>(
  fn: (...args: Args) => void,
  delayMs: number,
): Debouncer<Args> {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  const debounced = (...args: Args) => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      timeoutId = null;
      fn(...args);
    }, delayMs);
  };

  debounced.cancel = () => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
  };

  return debounced;
}
