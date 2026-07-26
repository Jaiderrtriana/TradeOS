import { apiRequest } from "../../api/client";

/** TRADEOS_API_SPECIFICATION.md §6.1 — request/response shapes, field-for-field. */
export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
}

export interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface RegisterResponse {
  user_id: string;
  email: string;
}

export function login(payload: LoginPayload): Promise<TokenPairResponse> {
  return apiRequest<TokenPairResponse>("/auth/login", { method: "POST", body: payload });
}

export function registerAccount(payload: RegisterPayload): Promise<RegisterResponse> {
  return apiRequest<RegisterResponse>("/auth/register", { method: "POST", body: payload });
}
