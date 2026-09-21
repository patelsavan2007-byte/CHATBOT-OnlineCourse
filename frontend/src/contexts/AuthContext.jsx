/**
 * Authentication context for the CHARUSAT Online Course Assistant.
 *
 * Provides:
 *  - user state (null = guest, object = authenticated)
 *  - loading state during initial auth check
 *  - login, signup, logout, googleLogin functions
 *  - isGuest, isAdmin computed flags
 *  - guest message tracking
 *  - dev auto-login on mount (development only)
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as authService from "../services/auth.js";
import { getAuthToken, clearAuth } from "../services/api.js";

const AuthContext = createContext(null);

const GUEST_LIMIT_KEY = "charusat_guest_count";
const GUEST_LIMIT = parseInt(import.meta.env.VITE_GUEST_MESSAGE_LIMIT || "4", 10);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // --- Initial auth check ---
  useEffect(() => {
    let cancelled = false;

    async function checkAuth() {
      const token = getAuthToken();

      if (token) {
        // We have a stored token — verify it
        try {
          const me = await authService.getMe();
          if (!cancelled) setUser(me);
        } catch {
          // Token invalid/expired
          clearAuth();
          // Try dev auto-login as fallback
          if (import.meta.env.DEV) {
            try {
              const me = await authService.devLogin();
              if (!cancelled) setUser(me);
            } catch {
              /* dev login not available */
            }
          }
        }
      } else if (import.meta.env.DEV) {
        // No token — try dev auto-login in development
        try {
          const me = await authService.devLogin();
          if (!cancelled) setUser(me);
        } catch {
          /* dev login not available — stay as guest */
        }
      }

      if (!cancelled) setLoading(false);
    }

    checkAuth();
    return () => { cancelled = true; };
  }, []);

  // --- Auth actions ---
  const login = useCallback(async (email, password) => {
    const me = await authService.login(email, password);
    setUser(me);
    return me;
  }, []);

  const signup = useCallback(async (name, email, password) => {
    const me = await authService.signup(name, email, password);
    setUser(me);
    return me;
  }, []);

  const googleLogin = useCallback(async (credential) => {
    const me = await authService.googleLogin(credential);
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    setUser(null);
    // Clear guest count on logout
    sessionStorage.removeItem(GUEST_LIMIT_KEY);
  }, []);

  // --- Guest message tracking ---
  const getGuestMessageCount = useCallback(() => {
    return parseInt(sessionStorage.getItem(GUEST_LIMIT_KEY) || "0", 10);
  }, []);

  const incrementGuestCount = useCallback(() => {
    const count = getGuestMessageCount() + 1;
    sessionStorage.setItem(GUEST_LIMIT_KEY, String(count));
    return count;
  }, [getGuestMessageCount]);

  const resetGuestCount = useCallback(() => {
    sessionStorage.removeItem(GUEST_LIMIT_KEY);
  }, []);

  const isGuestLimitReached = useCallback(() => {
    return getGuestMessageCount() >= GUEST_LIMIT;
  }, [getGuestMessageCount]);

  // --- Computed values ---
  const value = useMemo(
    () => ({
      user,
      loading,
      isGuest: !user,
      isAdmin: user?.role === "admin",
      login,
      signup,
      googleLogin,
      logout,
      setUser,
      guestLimit: GUEST_LIMIT,
      getGuestMessageCount,
      incrementGuestCount,
      resetGuestCount,
      isGuestLimitReached,
    }),
    [user, loading, login, signup, googleLogin, logout, getGuestMessageCount, incrementGuestCount, resetGuestCount, isGuestLimitReached],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

export default AuthContext;
