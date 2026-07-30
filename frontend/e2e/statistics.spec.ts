import { expect, test } from "@playwright/test";

/**
 * Cross-stack E2E — Sprint 6.2's deliverable, Milestone M6
 * (`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §7): the Statistics page's
 * three tabs, each wired to its own confirmed endpoint. Requires the
 * real backend running and migrated (same prerequisite as
 * e2e/mistakes.spec.ts).
 */

async function registerAndLogIn(page: import("@playwright/test").Page) {
  const uniqueEmail = `statistics-e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(uniqueEmail);
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("Email").fill(uniqueEmail);
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/$/);
}

async function createAndCloseTrade(
  page: import("@playwright/test").Page,
  market: string,
  result: "Take Profit" | "Stop Loss",
  exitPrice: string,
) {
  await page.goto("/trades");
  await page.getByRole("button", { name: "+ New Trade" }).click();
  const modal = page.getByRole("dialog");
  await modal.getByLabel("Market").fill(market);
  await modal.getByLabel("Direction").click();
  await page.getByRole("option", { name: "Long" }).click();
  await modal.getByLabel("Scoring Profile").click();
  await page.getByRole("option").first().click();
  await modal.getByLabel("Entry Price").fill("100");
  await modal.getByLabel("Stop Loss").fill("95");
  await modal.getByRole("button", { name: "Save Trade" }).click();
  await expect(page).toHaveURL(/\/trades\/[0-9a-f-]+$/);

  await page.getByRole("button", { name: "Close", exact: true }).click();
  const closeModal = page.getByRole("dialog");
  await closeModal.getByLabel("Result").click();
  await page.getByRole("option", { name: result }).click();
  await closeModal.getByLabel("Exit Price").fill(exitPrice);
  await closeModal.getByRole("button", { name: "Close Trade" }).click();
  await expect(page.getByText(result === "Take Profit" ? "TP" : "SL")).toBeVisible();
}

test("Statistics page's three tabs each reflect the same registered Trade", async ({ page }) => {
  await registerAndLogIn(page);
  const suffix = `${Date.now()}`;

  // entry=100/stop=95 (risk=5), TP at 110 -- r = +2.0, a clean win.
  await createAndCloseTrade(page, `S${suffix}`, "Take Profit", "110");

  await page.goto("/statistics");
  await expect(page.getByRole("heading", { name: "Statistics" })).toBeVisible();

  // Overview tab (default active): a MetricCard per StatisticsSummary field.
  await expect(page.getByText("Win Rate")).toBeVisible();
  await expect(page.getByText("100.0%")).toBeVisible();
  await expect(page.getByText("Expectancy (R)").first()).toBeVisible();

  // By Dimension tab: no strategy was set on the Trade -- buckets as
  // "Unassigned" under the default "Strategy" dimension.
  await page.getByRole("tab", { name: "By Dimension" }).click();
  await expect(page.getByRole("cell", { name: "Unassigned" })).toBeVisible();

  // Rolling tab: only one Trade exists, so `window=10` (the default)
  // sees every Trade -- Rolling and Overall must read identically.
  await page.getByRole("tab", { name: "Rolling" }).click();
  await expect(page.getByLabel("Window")).toBeVisible();
  const rollingRow = page.getByRole("row", { name: /^Rolling/ });
  const overallRow = page.getByRole("row", { name: /^Overall/ });
  await expect(rollingRow).toContainText("100.0%");
  await expect(overallRow).toContainText("100.0%");
});

test("an unauthenticated visitor is redirected away from /statistics", async ({ page }) => {
  await page.goto("/statistics");
  await expect(page).toHaveURL(/\/login$/);
});
