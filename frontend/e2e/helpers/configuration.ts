import type { Page } from "@playwright/test";

const API_BASE_URL = "http://localhost:8000/api/v1";

/**
 * Publishes a fresh, empty `ScoringConfigurationVersion` (zero criteria,
 * zero weights) so any spec that only needs `RegisterTradeUseCase`'s
 * precondition satisfied (`TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-03: a
 * Trade cannot be evaluated without a published Configuration) can do so
 * on its own, without depending on another spec file having already
 * published one.
 *
 * Deliberately the *lightest* version of the pattern
 * `evaluation-preview.spec.ts`'s own `createPublishedCriterion` already
 * established: that helper also creates a real, weighted criterion
 * because that suite asserts on actual score values. Specs using this
 * helper instead (trading/statistics/dashboard) never assert on a
 * score — only that the end-to-end flow completes and that
 * price-derived metrics (R-multiple, win rate) are correct — so an
 * empty, criterion-less published version is sufficient and keeps this
 * helper independent of any specific criterion/profile data.
 *
 * Safe under Playwright's `fullyParallel` execution: publishing is
 * guarded by a database-level advisory lock
 * (`ScoringConfigurationVersionRepository.lock_for_publish()`) plus a
 * partial unique index enforcing at most one published version at a time
 * (migration `0006`) — closed as
 * `ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md`. Concurrent calls from
 * different spec files/workers serialize instead of racing or
 * corrupting state.
 */
export async function ensurePublishedConfiguration(page: Page): Promise<void> {
  const accessToken = await page.evaluate(() => localStorage.getItem("tradeos.access_token"));
  const headers = { Authorization: `Bearer ${accessToken}` };

  const versionLabel = `e2e-${crypto.randomUUID().slice(0, 8)}`;
  const versionResponse = await page.request.post(`${API_BASE_URL}/configuration/versions`, {
    headers,
    data: { version_label: versionLabel },
  });
  if (!versionResponse.ok()) {
    throw new Error(`Failed to create configuration version: ${versionResponse.status()}`);
  }
  const version = await versionResponse.json();

  const publishResponse = await page.request.post(
    `${API_BASE_URL}/configuration/versions/${version.id}/publish`,
    { headers },
  );
  if (!publishResponse.ok()) {
    throw new Error(`Failed to publish configuration version: ${publishResponse.status()}`);
  }
}
