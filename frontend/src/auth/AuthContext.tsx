import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { clearTokens, getAccessToken, setTokens } from "./tokenStorage";

/**
 * Session state — TRADEOS_TECHNICAL_STACK.md §6.3: "UI state — plain React
 * state/Context, no library." Session/auth state has no server-cached
 * shape of its own (it's not data fetched from an endpoint), so it is UI
 * state, not a TanStack Query concern — same reasoning already applied to
 * ErrorContext in Sprint 0.3.
 */
interface AuthContextValue {
  isAuthenticated: boolean;
  login: (accessToken: string, refreshToken: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => getAccessToken() !== null);

  const login = useCallback((accessToken: string, refreshToken: string) => {
    setTokens(accessToken, refreshToken);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setIsAuthenticated(false);
  }, []);

  const value = useMemo(
    () => ({ isAuthenticated, login, logout }),
    [isAuthenticated, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
