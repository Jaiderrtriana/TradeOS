import { apiRequest } from "../../api/client";

/** TRADEOS_API_SPECIFICATION.md §6.3 — field-for-field. */
export interface PreferencesResponse {
  theme: string;
  language: string;
  notification_settings: Record<string, unknown>;
}

export interface UpdatePreferencesPayload {
  theme?: string;
  language?: string;
}

export function getPreferences(): Promise<PreferencesResponse> {
  return apiRequest<PreferencesResponse>("/preferences");
}

export function updatePreferences(payload: UpdatePreferencesPayload): Promise<PreferencesResponse> {
  return apiRequest<PreferencesResponse>("/preferences", { method: "PATCH", body: payload });
}
