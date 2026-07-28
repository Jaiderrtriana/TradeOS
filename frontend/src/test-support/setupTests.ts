import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";

/**
 * Vitest setup file (vite.config.ts's `test.setupFiles`) — registers
 * `@testing-library/jest-dom`'s matchers (`toBeInTheDocument()`, etc.)
 * globally, once, for every Component-tier test (Architecture Readiness
 * Review, three-tier testing strategy approved ahead of Sprint 4.4).
 * Unit-tier (pure-logic) tests never import anything from here.
 */

// `@testing-library/react`'s own auto-cleanup only self-registers when
// it detects a *global* `afterEach` (Vitest's `test.globals` is off in
// this project — vite.config.ts deliberately keeps every test file's
// `describe`/`it`/`expect` imports explicit, matching every existing
// test). Without this, one test's rendered DOM leaks into the next
// test's queries -- a real, reproducible failure this exact setup hit
// on its first run (`VirtualizedDataTable.test.tsx`'s empty-state test
// saw the *previous* test's table still mounted).
afterEach(() => {
  cleanup();
});

// jsdom does not implement `ResizeObserver` at all -- `VirtualizedDataTable`
// (`@tanstack/react-virtual`) needs the constructor to exist just to
// mount without throwing. A no-op stub is sufficient: component tests
// for that component deliberately don't assert on real virtualized-row
// rendering (jsdom has no real layout engine to make that meaningful) --
// see `VirtualizedDataTable.test.tsx`'s own docstring for why that's
// exercised at the E2E tier instead.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
