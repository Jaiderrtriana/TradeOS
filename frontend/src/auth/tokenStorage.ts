/**
 * Where access/refresh tokens live client-side.
 *
 * Approved decision (Sprint 1.2): localStorage for both tokens. Forced by
 * the already-frozen API contract — TRADEOS_API_SPECIFICATION.md §4.3
 * exchanges the refresh token via the POST /auth/refresh JSON *body*, not
 * an httpOnly cookie, so the client must be able to read it back with
 * JavaScript to resubmit it. That constraint rules out the httpOnly-cookie
 * pattern regardless of preference. If the API's refresh contract ever
 * changes to a cookie-based flow, this file is what must be revisited
 * (see CHANGELOG.md, Sprint 1.2).
 *
 * Plain functions, not a React hook: TRADEOS_FRONTEND_BLUEPRINT.md §2.2's
 * API client layer (api/client.ts) is not a React component and needs to
 * read the current token on every request without subscribing to context.
 */
const ACCESS_TOKEN_KEY = "tradeos.access_token";
const REFRESH_TOKEN_KEY = "tradeos.refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}
