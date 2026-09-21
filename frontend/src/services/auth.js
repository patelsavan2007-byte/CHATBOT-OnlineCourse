/**
 * Authentication service — handles signup, login, logout, and session management.
 */
import { apiFetch, setAuthToken, clearAuth } from "./api.js";

export async function login(email, password) {
  const data = await apiFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setAuthToken(data.token);
  return data.user;
}

export async function signup(name, email, password) {
  const data = await apiFetch("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
  setAuthToken(data.token);
  return data.user;
}

export async function getMe() {
  const data = await apiFetch("/api/auth/me");
  return data.user;
}

export async function devLogin() {
  const data = await apiFetch("/api/auth/dev-login", {
    method: "POST",
  });
  setAuthToken(data.token);
  return data.user;
}

export async function googleLogin(credential) {
  const data = await apiFetch("/api/auth/google", {
    method: "POST",
    body: JSON.stringify({ credential }),
  });
  setAuthToken(data.token);
  return data.user;
}

export async function logout() {
  try {
    await apiFetch("/api/auth/logout", { method: "POST" });
  } catch {
    /* ignore logout errors */
  }
  clearAuth();
}
