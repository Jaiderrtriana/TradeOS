import { networkError, parseApiError } from "./errors";

/**
 * The API client layer — TRADEOS_FRONTEND_BLUEPRINT.md §2.2: "the only
 * code permitted to know an endpoint's URL, method, and payload shape."
 * No feature module constructs a request manually.
 *
 * Sprint 0.3 scope: the generic request primitive and its error-envelope
 * handling only. No concrete endpoint function (login, trades, ...) exists
 * yet — those arrive with the module that owns them, per
 * TRADEOS_IMPLEMENTATION_MASTER_PLAN.md's phase ordering.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
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
