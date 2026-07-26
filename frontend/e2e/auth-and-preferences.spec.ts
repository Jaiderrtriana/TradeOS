import { expect, test } from "@playwright/test";

/**
 * Cross-stack E2E — TRADEOS_IMPLEMENTATION_MASTER_PLAN.md Sprint 1.2's own
 * named Phase 1 E2E test (§10, Testing Strategy): "UI walkthrough:
 * register, log in, change a preference." The sprint's deliverable is
 * explicitly "a first fully vertical (frontend-to-database) slice" — this
 * test is the only one in the project so far that requires the real
 * backend (FastAPI + Postgres) running, not just the frontend dev server.
 *
 * Prerequisite (documented, not automated by playwright.config.ts's
 * webServer, which manages only the Vite dev server): the backend must
 * already be running and reachable at the URL VITE_API_BASE_URL points to
 * (default http://localhost:8000/api/v1), with its database migrated.
 * See CHANGELOG.md, Sprint 1.2, for why this wasn't automated.
 */
test("a user can register, log in, and change a preference through the UI", async ({ page }) => {
  const uniqueEmail = `e2e-${Date.now()}@example.com`;

  await page.goto("/register");
  await page.getByLabel("Email").fill(uniqueEmail);
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("Email").fill(uniqueEmail);
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Sign in" }).click();

  // Successful login lands on the (protected) Dashboard placeholder at "/".
  await expect(page).toHaveURL(/\/$/);

  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Preferences" })).toBeVisible();

  // The trigger's text also contains the decorative "▾" icon, hence
  // toContainText rather than an exact-match toHaveText.
  const themeSelect = page.getByLabel("Theme");
  await expect(themeSelect).toContainText("Dark");
  await themeSelect.click();
  await page.getByRole("option", { name: "Light" }).click();
  await expect(themeSelect).toContainText("Light");

  // Reload — the changed preference must be read back from the backend,
  // not merely held in unpersisted client state.
  await page.reload();
  await expect(page.getByLabel("Theme")).toContainText("Light");
});

test("an unauthenticated visitor is redirected away from a protected route", async ({ page }) => {
  await page.goto("/settings");
  await expect(page).toHaveURL(/\/login$/);
});
