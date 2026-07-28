import { apiRequest } from "../../api/client";
import type { ScoringConfigurationVersion, ScoringWeight, UpdateDraftWeightPayload } from "./types";

/**
 * Configuration API wrappers — TRADEOS_API_SPECIFICATION.md §6.6, the
 * subset approved for Sprint 2.3's Scoring Versions page (view versions,
 * edit weights, publish). `listScoringCriteria`/`listScoringProfiles`
 * moved to `src/shared/scoringReferenceData.ts` (Architecture Readiness
 * Review, before Sprint 4.4) — see that module's own docstring.
 * Scoring criteria/profile CRUD (POST/PATCH `/scoring-criteria`,
 * POST `/scoring-profiles`) remains explicitly out of scope this
 * sprint — only reads were ever wired, since the weights editor only
 * needs to display which criterion/profile each weight belongs to.
 */

export function listConfigurationVersions(): Promise<ScoringConfigurationVersion[]> {
  return apiRequest<ScoringConfigurationVersion[]>("/configuration/versions");
}

export function createDraftConfigurationVersion(
  versionLabel: string,
): Promise<ScoringConfigurationVersion> {
  return apiRequest<ScoringConfigurationVersion>("/configuration/versions", {
    method: "POST",
    body: { version_label: versionLabel },
  });
}

export function listConfigurationWeights(versionId: string): Promise<ScoringWeight[]> {
  return apiRequest<ScoringWeight[]>(`/configuration/versions/${versionId}/weights`);
}

export function updateDraftWeight(
  versionId: string,
  payload: UpdateDraftWeightPayload,
): Promise<ScoringWeight> {
  return apiRequest<ScoringWeight>(`/configuration/versions/${versionId}/weights`, {
    method: "POST",
    body: payload,
  });
}

export function publishConfigurationVersion(
  versionId: string,
): Promise<ScoringConfigurationVersion> {
  return apiRequest<ScoringConfigurationVersion>(`/configuration/versions/${versionId}/publish`, {
    method: "POST",
  });
}
