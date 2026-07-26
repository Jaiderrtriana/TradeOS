import { defineConfig } from "@playwright/test";

// TRADEOS_TECHNICAL_STACK.md §10.1 — Playwright, the mandated E2E tool.
// Sprint 0.3 uses it for exactly one thing: proving the Exit Criteria that
// a simulated API error renders through the shared ErrorBanner path.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
  },
  webServer: {
    command: "pnpm dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
  },
});
