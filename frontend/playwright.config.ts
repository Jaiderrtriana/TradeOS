import { defineConfig } from "@playwright/test";

// TRADEOS_TECHNICAL_STACK.md §10.1 — Playwright, the mandated E2E tool.
// Sprint 0.3 uses it for exactly one thing: proving the Exit Criteria that
// a simulated API error renders through the shared ErrorBanner path.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  // `ScoringConfigurationVersion` is a deliberate global singleton (at
  // most one `published` row, ever — Product Bible's single-user
  // assumption, enforced by migration `0006`'s partial unique index).
  // Every spec file that creates a Trade now publishes its own version
  // via `e2e/helpers/configuration.ts` to be self-sufficient (no more
  // relying on another file having published one first), but different
  // spec files still run in separate, concurrent Playwright workers
  // against the SAME database — a publish from one file immediately
  // supersedes whatever another file's test was relying on being
  // published, mid-test. This is not new (already documented in
  // `evaluation-preview.spec.ts` and
  // `ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md` as a pre-existing,
  // previously-tolerated 2-file race); it became frequent enough to
  // reliably reproduce once more files independently publish. `workers:
  // 1` removes cross-file concurrency entirely, the same structural
  // preference this project's own backend fix already made (a database
  // constraint over trusting every caller) rather than adding
  // retries/staggering to individual specs.
  workers: 1,
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
