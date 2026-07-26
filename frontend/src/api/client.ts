import { getAccessToken } from "../auth/tokenStorage";
import { networkError, parseApiError } from "./errors";

/**
 * The API client layer — TRADEOS_FRONTEND_BLUEPRINT.md §2.2: "the only
 * code permitted to know an endpoint's URL, method, and payload shape."
 * No feature module constructs a request manually.
 *
 * Sprint 1.2: attaches `Authorization: Bearer <token>` automatically when
 * an access token is present (read from src/auth/tokenStorage.ts — see
 * that file for the localStorage decision and its rationale). No
 * automatic refresh-on-401 retry is implemented (approved scope for this
 * sprint) — a caller whose token has expired simply sees the 401.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const accessToken = getAccessToken();

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...options.headers,
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    // fetch() itself rejected — no response was ever received
    // (TRADEOS_FRONTEND_BLUEPRINT.md §17: "Network error", distinct from a
    // 500 the server actually sent).
    throw networkError();
  }

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // Response wasn't JSON at all — parseApiError's fallback handles this.
    }
    throw parseApiError(response.status, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
