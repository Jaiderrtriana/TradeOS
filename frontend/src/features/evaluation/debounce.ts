/**
 * A plain, framework-free debounce utility — deliberately not a React
 * hook, so its timing behavior is unit-testable with Vitest's fake timers
 * alone (TRADEOS_TECHNICAL_STACK.md §10: Vitest is named for pure-logic
 * tests, no DOM/component-rendering library is part of this stack).
 * `EvaluationPreviewForm` wires this into a `useEffect`; the scheduling
 * logic itself carries no React dependency to test around.
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
