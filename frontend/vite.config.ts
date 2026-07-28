/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// TRADEOS_SYSTEM_ARCHITECTURE.md §12.1: static hosting, no Node server at
// runtime (TRADEOS_TECHNICAL_STACK.md §6.1 — Vite chosen specifically for
// this: a pure client-side SPA build).
export default defineConfig({
  plugins: [react()],
  test: {
    // jsdom (not "node"): Architecture Readiness Review before Sprint 4.4
    // approved a three-tier testing strategy (Unit -> Component -> E2E) —
    // component tests (`@testing-library/react`) need a DOM. jsdom is a
    // strict superset for the pure-logic tests already written under
    // "node" (Sprint 0.3-3.3) — none of them touch `window`/`document`,
    // so switching the one shared environment doesn't change their
    // behavior, and keeps a single Vitest config rather than per-file
    // environment overrides.
    environment: "jsdom",
    setupFiles: ["./src/test-support/setupTests.ts"],
    exclude: ["e2e/**", "node_modules/**"],
  },
});
