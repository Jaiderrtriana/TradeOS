import { expect, test } from "@playwright/test";

/**
 * Cross-stack E2E — TRADEOS_IMPLEMENTATION_MASTER_PLAN.md Sprint 3.3's
 * deliverable: "a standalone, testable preview component." Requires the
 * real backend running and migrated (same prerequisite as
 * e2e/auth-and-preferences.spec.ts).
 *
 * Setup creates its own scoring criterion/version/weight via direct API
 * calls (Configuration's UI is read-only for criteria — "Creating/editing
 * ScoringCriterion definitions is explicitly out of scope,"
 * ScoringVersionsTab.tsx) — the same self-sufficient-fixture approach
 * `configuration-and-catalogs.spec.ts` uses, so this test never depends
 * on whatever seed data (or lack of it) already exists in the target
 * database.
 */

const API_BASE_URL = "http://localhost:8000/api/v1";

// Serialized deliberately: each test below publishes its own Configuration
// version (the only way to make a fresh criterion scoreable), and
// PublishScoringConfigurationVersionUseCase's "supersede the previous
// published version" step is a read-then-write sequence with no
// database-level constraint backing it (TRADEOS_DATABASE_DESIGN.md §6.6
// lists only `version_label` as a Unique Constraint -- no partial unique
// index on `status='published'`, unlike the equivalent pattern already
// used for `evaluation_snapshots.trade_id WHERE is_current = true`).
// Concurrent publishes reproduced two real failure modes: a crashing
// `sqlalchemy.exc.MultipleResultsFound` in `GetConfigurationVersionUseCase
// .get_published()` when two rows end up `status='published'`
// simultaneously, and -- observed running this file alongside
// `configuration-and-catalogs.spec.ts` (a *different* file, so this
// `serial` mode does not protect against it) -- silent data loss: whichever
// publish call's "supersede" finishes last wins, orphaning the other
// call's freshly-added weight from ever being evaluated, with no error at
// all. Both are genuine backend race conditions, out of scope to fix in
// this (frontend-only) sprint -- registered as discovered, unfixed
// technical debt (CHANGELOG.md, Sprint 3.3). This file passes reliably
// run in isolation (`playwright test e2e/evaluation-preview.spec.ts`);
// running the full E2E suite together can flake because of this
// pre-existing gap, not because of anything in this file.
test.describe.configure({ mode: "serial" });

async function registerAndLogIn(page: import("@playwright/test").Page) {
  const uniqueEmail = `eval-e2e-${Date.now()}@example.com`;
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

/**
 * Configuration data is global, not per-user
 * (`configuration-and-catalogs.spec.ts`'s own docstring) and this suite
 * runs with 4 parallel workers — `Date.now()` alone collides often enough
 * (millisecond resolution, near-simultaneous worker start) to 409 on
 * criterion/version creation and to make `getByLabel(name)` match more
 * than one leftover row from a previous run. `crypto.randomUUID()` is
 * unique per call regardless of timing; every unique-ID field below
 * (criterion id, source_field, criterion *name*, version label) uses the
 * same suffix so a field is never ambiguous to `getByLabel`.
 */
async function createPublishedCriterion(page: import("@playwright/test").Page, label: string) {
  // Sliced to 8 hex chars: `version_label` is capped at 40 chars
  // server-side (CreateScoringConfigurationVersionRequest), and a full
  // UUID plus the "e2e-eval-" prefix exceeds that.
  const uniqueSuffix = crypto.randomUUID().slice(0, 8);
  const sourceField = `e2e_field_${uniqueSuffix}`;
  const criterionName = `${label} ${uniqueSuffix}`;
  const criterionId = `confidence.${sourceField}`;

  const accessToken = await page.evaluate(() => localStorage.getItem("tradeos.access_token"));
  const headers = { Authorization: `Bearer ${accessToken}` };

  const criterionResponse = await page.request.post(
    `${API_BASE_URL}/configuration/scoring-criteria`,
    {
      headers,
      data: {
        id: criterionId,
        engine_type_code: "confidence",
        name: criterionName,
        source_field: sourceField,
        min_value: 0,
        max_value: 100,
      },
    },
  );
  if (!criterionResponse.ok()) {
    throw new Error(`Failed to create criterion: ${criterionResponse.status()}`);
  }

  const versionResponse = await page.request.post(`${API_BASE_URL}/configuration/versions`, {
    headers,
    data: { version_label: `e2e-eval-${uniqueSuffix}` },
  });
  if (!versionResponse.ok()) {
    throw new Error(`Failed to create version: ${versionResponse.status()}`);
  }
  const version = await versionResponse.json();

  const weightResponse = await page.request.post(
    `${API_BASE_URL}/configuration/versions/${version.id}/weights`,
    {
      headers,
      data: { criterion_id: criterionId, profile_code: "day_trading", weight: 1.0 },
    },
  );
  if (!weightResponse.ok()) {
    throw new Error(`Failed to add weight: ${weightResponse.status()}`);
  }

  const publishResponse = await page.request.post(
    `${API_BASE_URL}/configuration/versions/${version.id}/publish`,
    { headers },
  );
  if (!publishResponse.ok()) {
    throw new Error(`Failed to publish version: ${publishResponse.status()}`);
  }

  return criterionName;
}

test("filling the checklist updates the live preview after a debounce pause", async ({ page }) => {
  await registerAndLogIn(page);
  const criterionName = await createPublishedCriterion(page, "E2E Confidence Field");

  await page.goto("/evaluation");
  await expect(page.getByRole("heading", { name: "Evaluation Preview" })).toBeVisible();

  await page.getByText("Confidence", { exact: true }).click(); // expand the collapsible engine group
  await page.getByLabel(criterionName).fill("100");

  await expect(page.getByTestId("score-ring-confidence")).toContainText("100", { timeout: 3000 });
  await expect(page.getByTestId("score-ring-confidence")).toContainText("A+");
});

test("rapid edits collapse into a single backend call (debounce)", async ({ page }) => {
  await registerAndLogIn(page);
  const criterionName = await createPublishedCriterion(page, "E2E Debounce Field");

  let previewRequestCount = 0;
  await page.route("**/api/v1/evaluation/preview", (route) => {
    previewRequestCount += 1;
    void route.continue();
  });

  await page.goto("/evaluation");
  await page.getByText("Confidence", { exact: true }).click();

  const field = page.getByLabel(criterionName);
  await field.fill("10");
  await field.fill("20");
  await field.fill("30");
  await field.fill("40");

  // Only the last value should ever reach the backend, in exactly one call.
  await expect(page.getByTestId("score-ring-confidence")).toContainText("40", { timeout: 3000 });
  expect(previewRequestCount).toBe(1);
});

test("the checklist stays editable and recovers after a transient preview failure", async ({
  page,
}) => {
  await registerAndLogIn(page);
  const criterionName = await createPublishedCriterion(page, "E2E Error Field");

  let failNext = true;
  await page.route("**/api/v1/evaluation/preview", (route) => {
    if (failNext) {
      failNext = false;
      void route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "INTERNAL_ERROR", message: "boom", details: [], trace_id: null },
        }),
      });
    } else {
      void route.continue();
    }
  });

  await page.goto("/evaluation");
  await page.getByText("Confidence", { exact: true }).click();

  const field = page.getByLabel(criterionName);
  await field.fill("50");

  await expect(page.getByRole("alert")).toBeVisible({ timeout: 3000 });
  // The failure never disables the field -- the user can keep typing.
  await expect(field).toBeEnabled();

  // A new debounced request (triggered by the next edit) succeeds and
  // clears the error.
  await field.fill("60");
  await expect(page.getByTestId("score-ring-confidence")).toContainText("60", { timeout: 3000 });
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("an unauthenticated visitor is redirected away from /evaluation", async ({ page }) => {
  await page.goto("/evaluation");
  await expect(page).toHaveURL(/\/login$/);
});
