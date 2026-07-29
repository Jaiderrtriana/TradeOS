import { expect, test } from "@playwright/test";

/**
 * Cross-stack E2E — Sprint 5.1's deliverable, Milestone M5
 * (`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §7): "Journal entries
 * (trade-scoped and period-scoped)... function against real Trade
 * data." Requires the real backend running and migrated (same
 * prerequisite as e2e/auth-and-preferences.spec.ts).
 */

async function registerAndLogIn(page: import("@playwright/test").Page) {
  const uniqueEmail = `journal-e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
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

async function createTradeSimple(page: import("@playwright/test").Page, market: string) {
  await page.goto("/trades");
  await page.getByRole("button", { name: "+ New Trade" }).click();
  const modal = page.getByRole("dialog");
  await expect(modal.getByRole("heading", { name: "New Trade" })).toBeVisible();

  await modal.getByLabel("Market").fill(market);
  await modal.getByLabel("Direction").click();
  await page.getByRole("option", { name: "Long" }).click();
  await modal.getByLabel("Scoring Profile").click();
  await page.getByRole("option").first().click();
  await modal.getByLabel("Entry Price").fill("100");
  await modal.getByLabel("Stop Loss").fill("95");

  await modal.getByRole("button", { name: "Save Trade" }).click();
  await expect(page).toHaveURL(/\/trades\/[0-9a-f-]+$/);
}

test("golden path: write, edit, and delete a period-scoped entry from Journal List", async ({
  page,
}) => {
  await registerAndLogIn(page);

  await page.goto("/journal");
  await expect(page.getByRole("heading", { name: "Journal" })).toBeVisible();
  await page.getByRole("button", { name: "+ New Entry" }).click();

  const modal = page.getByRole("dialog");
  await expect(modal.getByRole("heading", { name: "New Journal Entry (Period)" })).toBeVisible();
  await modal.getByLabel("Period Start").fill("2026-07-20");
  await modal.getByLabel("Period End").fill("2026-07-26");
  await modal.getByLabel("Content").fill("Overtraded on Tuesday, stuck to the plan otherwise.");
  await modal.getByRole("button", { name: "Save Entry" }).click();

  const row = page.getByRole("row", { name: /Overtraded on Tuesday/ });
  await expect(row).toBeVisible();
  await row.click();

  await expect(page).toHaveURL(/\/journal\/[0-9a-f-]+$/);
  await expect(page.getByText(/Period: 2026-07-20 – 2026-07-26/)).toBeVisible();
  await expect(page.getByText("Overtraded on Tuesday, stuck to the plan otherwise.")).toBeVisible();

  await page.getByRole("button", { name: "Edit" }).click();
  const editModal = page.getByRole("dialog");
  await expect(editModal.getByRole("heading", { name: "Edit Journal Entry" })).toBeVisible();
  await editModal.getByLabel("Content").fill("Edited: stuck to the plan the whole week.");
  await editModal.getByRole("button", { name: "Save Entry" }).click();
  await expect(page.getByText("Edited: stuck to the plan the whole week.")).toBeVisible();

  await page.getByRole("button", { name: "Delete" }).click();
  const confirmDialog = page.getByRole("alertdialog");
  await expect(confirmDialog).toBeVisible();
  await confirmDialog.getByRole("button", { name: "Delete" }).click();
  await expect(page).toHaveURL(/\/journal$/);
});

test("a trade-scoped entry can be created from Trade Detail and shows there", async ({ page }) => {
  await registerAndLogIn(page);
  const market = `J${Date.now()}`;
  await createTradeSimple(page, market);

  await page.getByRole("button", { name: "+ Journal Entry" }).click();
  const modal = page.getByRole("dialog");
  await expect(modal.getByRole("heading", { name: "New Journal Entry" })).toBeVisible();
  await modal.getByLabel("Content").fill("Entered on the retest, exactly per plan.");
  await modal.getByRole("button", { name: "Save Entry" }).click();

  await expect(page.getByText(/Entered on the retest/)).toBeVisible();
});

test("an unauthenticated visitor is redirected away from /journal", async ({ page }) => {
  await page.goto("/journal");
  await expect(page).toHaveURL(/\/login$/);
});
