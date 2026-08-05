import { expect, test } from "@playwright/test";

/**
 * Cross-stack E2E — Sprint 4.4's deliverable, Milestone M4
 * (`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §7): "A trader logs a Trade
 * through the frontend (Simple or Pro), it is scored synchronously by
 * all active engines, closed, re-evaluated once, and a Mistake is
 * tagged to it — all without a silent failure." Requires the real
 * backend running and migrated (same prerequisite as
 * e2e/auth-and-preferences.spec.ts).
 *
 * Uses `day_trading`, one of the 3 `scoring_profiles` seeded by
 * migration `0004` — no Configuration setup needed for Simple mode
 * (unlike evaluation-preview.spec.ts, which needs a published criterion
 * to see a non-zero score; this suite doesn't assert on score values,
 * only that the end-to-end flow completes).
 */

const API_BASE_URL = "http://localhost:8000/api/v1";

async function registerAndLogIn(page: import("@playwright/test").Page) {
  const uniqueEmail = `trading-e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
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

async function createMistakeTagEntry(page: import("@playwright/test").Page, name: string) {
  const accessToken = await page.evaluate(() => localStorage.getItem("tradeos.access_token"));
  const response = await page.request.post(`${API_BASE_URL}/catalogs`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    data: { kind: "mistake_tag", name },
  });
  if (!response.ok()) {
    throw new Error(`Failed to create mistake tag entry: ${response.status()}`);
  }
}

async function createTradeSimple(page: import("@playwright/test").Page, market: string) {
  await page.goto("/trades");
  await page.getByRole("button", { name: "+ New Trade" }).click();
  const modal = page.getByRole("dialog");
  await expect(modal.getByRole("heading", { name: "New Trade" })).toBeVisible();

  await modal.getByLabel("Market").fill(market);
  await modal.getByLabel("Direction").click();
  await page.getByRole("option", { name: "Long" }).click();
  // Trade Status defaults to "Open" (useTradeEntryForm's v2.0 default) --
  // no interaction needed unless a test wants Planned/Closed explicitly.
  await modal.getByLabel("Trade Type").click();
  await page.getByRole("option").first().click();
  await modal.getByLabel("Entry Price").fill("100");
  await modal.getByLabel("Stop Loss").fill("95");
  await modal.getByLabel("Entry Date").fill("2026-01-01");

  await modal.getByRole("button", { name: "Save Trade" }).click();
  await expect(page).toHaveURL(/\/trades\/[0-9a-f-]+$/);
}

test("golden path: create, tag a mistake, close, re-evaluate, view the Rule Explorer", async ({
  page,
}) => {
  await registerAndLogIn(page);
  const market = `E2E-${Date.now()}`;
  const mistakeName = `E2E Mistake ${Date.now()}`;
  await createMistakeTagEntry(page, mistakeName);

  await createTradeSimple(page, market);

  // Trade Detail: the summary and a computed (if scoreless) Evaluation
  // are both present immediately -- POST /trades is synchronous.
  await expect(page.getByRole("heading", { name: market })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evaluation" })).toBeVisible();
  await expect(page.getByTestId("score-ring-confidence")).toBeVisible();

  // Tag a mistake.
  await page.getByRole("button", { name: "+ Add" }).click();
  const pickerModal = page.getByRole("dialog");
  await expect(pickerModal.getByRole("heading", { name: "Tag a Mistake" })).toBeVisible();
  await pickerModal.getByRole("button", { name: mistakeName }).click();
  await expect(page.getByText(mistakeName)).toBeVisible();

  // Close the trade.
  await page.getByRole("button", { name: "Close", exact: true }).click();
  const closeModal = page.getByRole("dialog");
  await expect(closeModal.getByRole("heading", { name: "Close Trade" })).toBeVisible();
  await closeModal.getByLabel("Result").click();
  await page.getByRole("option", { name: "Take Profit" }).click();
  await closeModal.getByLabel("Exit Price").fill("110");
  await closeModal.getByLabel("Realized P&L").fill("100");
  await closeModal.getByLabel("Close Date").fill("2026-01-02");
  await closeModal.getByRole("button", { name: "Close Trade" }).click();
  await expect(page.getByText("TP")).toBeVisible();
  // Close is no longer offered once the trade is no longer open.
  await expect(page.getByRole("button", { name: "Close", exact: true })).toHaveCount(0);

  // Re-evaluate.
  await page.getByRole("button", { name: "Re-evaluate" }).click();
  const reevaluateModal = page.getByRole("dialog");
  await expect(reevaluateModal.getByRole("heading", { name: "Re-evaluate Trade" })).toBeVisible();
  await reevaluateModal.getByLabel("Scoring Profile").click();
  await page.getByRole("option").first().click();
  await reevaluateModal.getByRole("button", { name: "Re-evaluate", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Re-evaluate Trade" })).toHaveCount(0);

  // Rule Explorer: current snapshot, then history shows at least the
  // re-evaluated entry.
  await page.getByRole("link", { name: "View full breakdown" }).click();
  await expect(page).toHaveURL(/\/trades\/[0-9a-f-]+\/evaluation$/);
  await expect(page.getByTestId("score-ring-confidence")).toBeVisible();

  await page.getByRole("tab", { name: "History" }).click();
  await expect(page.getByRole("row").first()).toBeVisible();
  await page.getByRole("row").nth(1).click();
  await expect(page.getByTestId("score-ring-confidence").last()).toBeVisible();
});

test("Trades List shows a created trade and navigates to its detail on click", async ({ page }) => {
  await registerAndLogIn(page);
  // `market` is capped at 20 chars server-side (RegisterTradeRequest) --
  // "L" + a 13-digit timestamp keeps this under that limit.
  const market = `L${Date.now()}`;
  await createTradeSimple(page, market);

  await page.goto("/trades");
  const row = page.getByRole("row", { name: new RegExp(market) });
  await expect(row).toBeVisible();
  await row.click();
  await expect(page).toHaveURL(/\/trades\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: market })).toBeVisible();
});

test("Planned trade has no Evaluation until opened, then Open runs it for the first time", async ({
  page,
}) => {
  await registerAndLogIn(page);
  const market = `PL${Date.now()}`;

  await page.goto("/trades");
  await page.getByRole("button", { name: "+ New Trade" }).click();
  const modal = page.getByRole("dialog");
  await expect(modal.getByRole("heading", { name: "New Trade" })).toBeVisible();

  await modal.getByLabel("Market").fill(market);
  await modal.getByLabel("Direction").click();
  await page.getByRole("option", { name: "Long" }).click();
  await modal.getByLabel("Trade Status").click();
  await page.getByRole("option", { name: "Planned" }).click();
  // Trade Type/Entry Price/Stop Loss/Entry Date are all hidden while
  // Planned -- nothing else to fill in.
  await modal.getByRole("button", { name: "Save Trade" }).click();
  await expect(page).toHaveURL(/\/trades\/[0-9a-f-]+$/);

  await expect(page.getByRole("heading", { name: market })).toBeVisible();
  await expect(page.getByText("PLANNED", { exact: true })).toBeVisible();
  await expect(page.getByText("still Planned")).toBeVisible();
  // Only Amend/Open/Delete are offered for a Planned trade -- no Close,
  // no Re-evaluate (Domain Invariant DI-13: no Evaluation exists yet).
  await expect(page.getByRole("button", { name: "Close", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Re-evaluate" })).toHaveCount(0);

  await page.getByRole("button", { name: "Open", exact: true }).click();
  const openModal = page.getByRole("dialog");
  await expect(openModal.getByRole("heading", { name: "Open Trade" })).toBeVisible();
  await openModal.getByLabel("Trade Type").click();
  await page.getByRole("option").first().click();
  await openModal.getByLabel("Entry Price").fill("100");
  await openModal.getByLabel("Stop Loss").fill("95");
  await openModal.getByLabel("Entry Date").fill("2026-01-01");
  await openModal.getByRole("button", { name: "Open Trade" }).click();

  await expect(page.getByText("OPEN", { exact: true })).toBeVisible();
  await expect(page.getByTestId("score-ring-confidence")).toBeVisible();
  await expect(page.getByRole("button", { name: "Close", exact: true })).toBeVisible();
});

test("submitting without a Trade Type prompts the just-in-time TradeTypeDialog", async ({
  page,
}) => {
  await registerAndLogIn(page);
  const market = `TT${Date.now()}`;

  await page.goto("/trades");
  await page.getByRole("button", { name: "+ New Trade" }).click();
  const modal = page.getByRole("dialog");
  await expect(modal.getByRole("heading", { name: "New Trade" })).toBeVisible();

  await modal.getByLabel("Market").fill(market);
  await modal.getByLabel("Direction").click();
  await page.getByRole("option", { name: "Long" }).click();
  // Trade Type deliberately left empty.
  await modal.getByLabel("Entry Price").fill("100");
  await modal.getByLabel("Stop Loss").fill("95");
  await modal.getByLabel("Entry Date").fill("2026-01-01");

  await modal.getByRole("button", { name: "Save Trade" }).click();

  const typeDialog = page.getByRole("dialog").filter({ hasText: "Select a Trade Type" });
  await expect(typeDialog.getByRole("heading", { name: "Select a Trade Type" })).toBeVisible();
  await typeDialog.getByLabel("Trade Type").click();
  await page.getByRole("option").first().click();
  await typeDialog.getByRole("button", { name: "Continue" }).click();

  await expect(page).toHaveURL(/\/trades\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: market })).toBeVisible();
});

test("an unauthenticated visitor is redirected away from /trades", async ({ page }) => {
  await page.goto("/trades");
  await expect(page).toHaveURL(/\/login$/);
});
