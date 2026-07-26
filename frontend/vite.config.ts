/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// TRADEOS_SYSTEM_ARCHITECTURE.md §12.1: static hosting, no Node server at
// runtime (TRADEOS_TECHNICAL_STACK.md §6.1 — Vite chosen specifically for
// this: a pure client-side SPA build).
export default defineConfig({
  plugins: [react()],
  test: {
    // Pure-logic tests only (TRADEOS_TECHNICAL_STACK.md §10 names Vitest,
    // not a DOM/component-rendering library) — no jsdom environment needed
    // for Sprint 0.3's parseApiError tests.
    environment: "node",
    exclude: ["e2e/**", "node_modules/**"],
  },
});
