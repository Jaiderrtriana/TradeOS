import { apiRequest } from "../../api/client";
import type {
  ScoringConfigurationVersion,
  ScoringCriterion,
  ScoringProfile,
  ScoringWeight,
  UpdateDraftWeightPayload,
} from "./types";

/**
 * Configuration API wrappers — TRADEOS_API_SPECIFICATION.md §6.6, the
 * subset approved for Sprint 2.3's Scoring Versions page (view versions,
 * view criteria/profiles as reference, create draft, edit weights,
 * publish). Scoring criteria/profile CRUD (POST/PATCH `/scoring-criteria`,
 * POST `/scoring-profiles`) is explicitly out of scope this sprint — only
 * their read endpoints are wired, since the weights editor needs to
 * display which criterion/profile each weight belongs to.
 */

export function listScoringProfiles(): Promise<ScoringProfile[]> {
  return apiRequest<ScoringProfile[]>("/configuration/scoring-profiles");
}

export function listScoringCriteria(): Promise<ScoringCriterion[]> {
  return apiRequest<ScoringCriterion[]>("/configuration/scoring-criteria");
}

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
