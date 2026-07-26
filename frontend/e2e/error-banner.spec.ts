import { expect, test } from "@playwright/test";

/**
 * Proves Sprint 0.3's second Exit Criteria
 * (TRADEOS_IMPLEMENTATION_MASTER_PLAN.md, Phase 0): a simulated API error
 * renders through the one shared error path, not a page-specific handler.
 *
 * No real endpoint exists yet, so the error is triggered via a dev-only
 * test hook (src/test-support/errorSimulation.ts) that calls the exact
 * same parseApiError -> ErrorContext -> ErrorBanner path a real failed
 * request will use starting Phase 1.
 */
test("a simulated API error renders through the shared ErrorBanner", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByTestId("error-banner")).toHaveCount(0);

  await page.evaluate(() => window.__tradeosSimulateApiError?.());

  const banner = page.getByTestId("error-banner");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("Something went wrong on our end.");
  await expect(banner).toContainText("test-trace-id-0001");
});

test("the same banner renders identically from a different route", async ({ page }) => {
  // Proves it's the one shared path, not a page-specific handler wired
  // only into the Dashboard placeholder.
  await page.goto("/trades");

  await page.evaluate(() => window.__tradeosSimulateApiError?.());

  await expect(page.getByTestId("error-banner")).toBeVisible();
});
