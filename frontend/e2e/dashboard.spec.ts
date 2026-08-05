import { expect, test } from "@playwright/test";

/**
 * Cross-stack E2E — Sprint 8.1's deliverable, Milestone M8
 * (`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §7): the Dashboard as the
 * post-login landing page, composing Statistics/Mistakes/Trading into
 * one screen. Requires the real backend running and migrated (same
 * prerequisite as e2e/statistics.spec.ts).
 */

async function registerAndLogIn(page: import("@playwright/test").Page) {
  const uniqueEmail = `dashboard-e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
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
  await modal.getByLabel("Trade Type").click();
  await page.getByRole("option").first().click();
  await modal.getByLabel("Entry Price").fill("100");
  await modal.getByLabel("Stop Loss").fill("95");
  await modal.getByLabel("Entry Date").fill("2026-01-01");
  await modal.getByRole("button", { name: "Save Trade" }).click();
  await expect(page).toHaveURL(/\/trades\/[0-9a-f-]+$/);

  await page.getByRole("button", { name: "Close", exact: true }).click();
  const closeModal = page.getByRole("dialog");
  await closeModal.getByLabel("Result").click();
  await page.getByRole("option", { name: result }).click();
  await closeModal.getByLabel("Exit Price").fill(exitPrice);
  await closeModal.getByLabel("Realized P&L").fill("0");
  await closeModal.getByLabel("Close Date").fill("2026-01-02");
  await closeModal.getByRole("button", { name: "Close Trade" }).click();
  await expect(page.getByText(result === "Take Profit" ? "TP" : "SL")).toBeVisible();
}

test("Dashboard shows the empty state for a fresh user with no Trades", async ({ page }) => {
  await registerAndLogIn(page);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("Log your first trade to see your dashboard.")).toBeVisible();
});

test("Dashboard composes metrics and a recent Trades preview after logging a Trade", async ({
  page,
}) => {
  await registerAndLogIn(page);
  const suffix = `${Date.now()}`;

  // entry=100/stop=95 (risk=5), TP at 110 -- r = +2.0, a clean win.
  await createAndCloseTrade(page, `D${suffix}`, "Take Profit", "110");

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("Win Rate")).toBeVisible();
  await expect(page.getByText("100.0%")).toBeVisible();

  await expect(page.getByText(`D${suffix}`)).toBeVisible();
  await page.getByText(`D${suffix}`).click();
  await expect(page).toHaveURL(/\/trades\/[0-9a-f-]+$/);
});

test("an unauthenticated visitor is redirected away from the Dashboard", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
});
