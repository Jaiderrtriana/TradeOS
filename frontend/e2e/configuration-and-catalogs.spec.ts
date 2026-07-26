import { expect, test } from "@playwright/test";

/**
 * Cross-stack E2E — Sprint 2.3's deliverable: "an admin-facing screen
 * pair fully wired to Sprints 2.1-2.2's endpoints." Requires the real
 * backend running and migrated (same prerequisite as
 * e2e/auth-and-preferences.spec.ts — see that file's docstring).
 *
 * Configuration/Catalogs data is global, not per-user
 * (TRADEOS_API_SPECIFICATION.md §4.6) — every test uses a unique
 * label/name so it never collides with data another test run, or the
 * real Sprint 2.1/2.2 seed (`v1.0`, the 37 real catalog entries), already
 * left behind in the shared dev database.
 */

async function registerAndLogIn(page: import("@playwright/test").Page) {
  const uniqueEmail = `config-e2e-${Date.now()}@example.com`;
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

test("a trader can create a draft version, add a weight, and publish it", async ({ page }) => {
  await registerAndLogIn(page);
  await page.goto("/configuration");
  await expect(page.getByRole("heading", { name: "Scoring Configuration" })).toBeVisible();

  const versionLabel = `e2e-v-${Date.now()}`;
  await page.getByLabel("New draft label").fill(versionLabel);
  await page.getByRole("button", { name: "+ New Draft" }).click();

  const versionRow = page.getByRole("row", { name: new RegExp(versionLabel) });
  await expect(versionRow).toBeVisible();
  await expect(versionRow.getByText("draft")).toBeVisible();

  // Creating a draft auto-selects it, so its detail panel — the inline
  // expansion approved for Sprint 2.3 (no Drawer, no nested route) — is
  // already open; a row click here would toggle it back closed.
  await expect(page.getByText(`${versionLabel} — criteria & weights`)).toBeVisible();

  await page.getByLabel("Criterion").click();
  await page.getByRole("option").first().click();
  await page.getByLabel("Profile").click();
  await page.getByRole("option").first().click();
  await page.getByLabel("Weight").fill("0.5");
  await page.getByRole("button", { name: "Add / Update Weight" }).click();

  await expect(page.getByText("No weights added to this version yet.")).toHaveCount(0);

  await page.getByRole("button", { name: "Publish" }).click();
  const confirmDialog = page.getByRole("alertdialog");
  await expect(confirmDialog).toBeVisible();
  await confirmDialog.getByRole("button", { name: "Publish" }).click();

  await expect(versionRow.getByText("published")).toBeVisible();
});

test("a trader can add and deactivate a catalog entry", async ({ page }) => {
  await registerAndLogIn(page);
  await page.goto("/configuration");
  await page.getByRole("tab", { name: "Catalogs Management" }).click();
  await expect(page.getByRole("heading", { name: "Catalogs Management" })).toBeVisible();

  const entryName = `E2E Setup ${Date.now()}`;
  await page.getByLabel("New entry kind").click();
  await page.getByRole("option", { name: "Setup" }).click();
  await page.getByLabel("Name").fill(entryName);
  await page.getByRole("button", { name: "+ Add" }).click();

  const entryRow = page.getByRole("row", { name: new RegExp(entryName) });
  await expect(entryRow).toBeVisible();
  await expect(entryRow.getByText("Active")).toBeVisible();

  await entryRow.getByRole("button", { name: "Deactivate" }).click();
  await expect(entryRow.getByText("Inactive")).toBeVisible();
});

test("an unauthenticated visitor is redirected away from /configuration", async ({ page }) => {
  await page.goto("/configuration");
  await expect(page).toHaveURL(/\/login$/);
});
