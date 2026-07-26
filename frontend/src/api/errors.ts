/**
 * The one error shape every TradeOS API response returns on failure
 * (TRADEOS_API_SPECIFICATION.md §8) — mirrored here field-for-field.
 */
export interface ApiErrorDetail {
  field?: string;
  issue?: string;
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details: ApiErrorDetail[];
    trace_id: string | null;
    timestamp: string;
  };
}

/**
 * Client-side-only codes for failure modes the backend never produces:
 * the request never got a response at all, or a response arrived that
 * doesn't match the documented envelope shape. Kept in the same `code`
 * space as the backend's own categories (TRADEOS_API_SPECIFICATION.md §8)
 * so ErrorBanner has exactly one thing to switch on, never two.
 */
export const NETWORK_ERROR_CODE = "NETWORK_ERROR";
export const UNKNOWN_ERROR_CODE = "UNKNOWN_ERROR";

export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string;
  readonly details: ApiErrorDetail[];
  readonly traceId: string | null;

  constructor(params: {
    status: number | null;
    code: string;
    message: string;
    details?: ApiErrorDetail[];
    traceId?: string | null;
  }) {
    super(params.message);
    this.name = "ApiError";
    this.status = params.status;
    this.code = params.code;
    this.details = params.details ?? [];
    this.traceId = params.traceId ?? null;
  }
}

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (typeof value !== "object" || value === null || !("error" in value)) {
    return false;
  }
  const error = (value as { error: unknown }).error;
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    "message" in error &&
    typeof (error as { code: unknown }).code === "string" &&
    typeof (error as { message: unknown }).message === "string"
  );
}

/**
 * Normalizes any failed API response into one ApiError shape — the single
 * function every caller (the API client, and eventually every feature
 * module) funnels through, so error presentation is never page-specific
 * (TRADEOS_FRONTEND_BLUEPRINT.md §2.8, §17).
 */
export function parseApiError(status: number, body: unknown): ApiError {
  if (isApiErrorEnvelope(body)) {
    return new ApiError({
      status,
      code: body.error.code,
      message: body.error.message,
      details: body.error.details,
      traceId: body.error.trace_id,
    });
  }

  return new ApiError({
    status,
    code: UNKNOWN_ERROR_CODE,
    message: "The server returned an unexpected error response.",
  });
}

/** For fetch() failures where no response was ever received at all. */
export function networkError(message = "Could not reach the server."): ApiError {
  return new ApiError({ status: null, code: NETWORK_ERROR_CODE, message });
}
