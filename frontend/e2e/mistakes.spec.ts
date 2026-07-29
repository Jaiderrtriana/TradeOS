import { expect, test } from "@playwright/test";

/**
 * Cross-stack E2E — Sprint 5.2's deliverable, Milestone M5
 * (`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` §7): "the Mistake priority
 * ranking... function[s] against real Trade data." Requires the real
 * backend running and migrated (same prerequisite as
 * e2e/auth-and-preferences.spec.ts).
 *
 * The core assertion this file exists to make: `Priority` is a stable,
 * cost-based rank that does **not** change when the visible row order
 * is re-sorted by Frequency instead — the approved architectural
 * decision distinguishing "Priority" from "current table row index."
 */

async function registerAndLogIn(page: import("@playwright/test").Page) {
  const uniqueEmail = `mistakes-e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
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

async function tagMistake(page: import("@playwright/test").Page, tagName: string) {
  await page.getByRole("button", { name: "+ Add" }).click();
  const pickerModal = page.getByRole("dialog");
  await expect(pickerModal.getByRole("heading", { name: "Tag a Mistake" })).toBeVisible();
  await pickerModal.getByRole("button", { name: tagName }).click();
  await expect(page.getByText(tagName)).toBeVisible();
}

async function createMistakeTagEntry(page: import("@playwright/test").Page, name: string) {
  const accessToken = await page.evaluate(() => localStorage.getItem("tradeos.access_token"));
  const response = await page.request.post("http://localhost:8000/api/v1/catalogs", {
    headers: { Authorization: `Bearer ${accessToken}` },
    data: { kind: "mistake_tag", name },
  });
  if (!response.ok()) {
    throw new Error(`Failed to create mistake tag entry: ${response.status()}`);
  }
}

test("priority stays stable when the visible sort changes from Cost to Frequency", async ({
  page,
}) => {
  await registerAndLogIn(page);
  const suffix = `${Date.now()}`;
  const fomoTag = `FOMO-${suffix}`;
  const movedStopTag = `MovedStop-${suffix}`;
  await createMistakeTagEntry(page, fomoTag);
  await createMistakeTagEntry(page, movedStopTag);

  // FOMO: two trades, net cost = +2.0 + -1.0 = +1.0, frequency 2.
  await createAndCloseTrade(page, `M${suffix}A`, "Take Profit", "110");
  await tagMistake(page, fomoTag);

  await createAndCloseTrade(page, `M${suffix}B`, "Stop Loss", "95");
  await tagMistake(page, fomoTag);
  await tagMistake(page, movedStopTag); // MovedStop: cost -1.0, frequency 1.

  await page.goto("/mistakes");
  await expect(page.getByRole("heading", { name: "Mistakes Ranking" })).toBeVisible();

  // Default sort is Cost (most costly first): MovedStop (-1.0) ranks
  // above FOMO (+1.0), so MovedStop is Priority #1, FOMO is #2.
  const movedStopRow = page.getByRole("row", { name: new RegExp(movedStopTag) });
  const fomoRow = page.getByRole("row", { name: new RegExp(fomoTag) });
  await expect(movedStopRow).toContainText("#1");
  await expect(fomoRow).toContainText("#2");

  // Switch to Frequency (most frequent first): FOMO (frequency 2) now
  // appears first in the table -- but its Priority must still read #2,
  // and MovedStop's must still read #1. The row order changed; the
  // Priority values did not.
  await page.getByLabel("Sort by").click();
  await page.getByRole("option", { name: "Frequency (most frequent first)" }).click();

  const rows = page.getByRole("row");
  await expect(rows.nth(1)).toContainText(fomoTag);
  await expect(fomoRow).toContainText("#2");
  await expect(movedStopRow).toContainText("#1");
});

test("an unauthenticated visitor is redirected away from /mistakes", async ({ page }) => {
  await page.goto("/mistakes");
  await expect(page).toHaveURL(/\/login$/);
});
