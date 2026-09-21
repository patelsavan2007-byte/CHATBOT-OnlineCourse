/**
 * Centralized API client for the CHARUSAT Online Course Assistant.
 *
 * All HTTP requests go through this module so auth headers, error handling,
 * and base URL configuration are centralized in one place.
 */

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Token management
// ---------------------------------------------------------------------------

let _token = localStorage.getItem("auth_token");

export function setAuthToken(token) {
  _token = token;
  if (token) {
    localStorage.setItem("auth_token", token);
  } else {
    localStorage.removeItem("auth_token");
  }
}

export function getAuthToken() {
  return _token;
}

export function clearAuth() {
  _token = null;
  localStorage.removeItem("auth_token");
}

// ---------------------------------------------------------------------------
// Base fetch wrapper
// ---------------------------------------------------------------------------

/**
 * Make an authenticated API request.
 * Automatically attaches JWT token if available.
 * Throws on non-OK responses with parsed error detail.
 */
export async function apiFetch(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  }

  const url = path.startsWith("/api") ? `${API_BASE}${path}` : `${API_BASE}${path}`;

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* keep default message */
    }

    // Handle unauthorized — clear auth state
    if (res.status === 401) {
      clearAuth();
    }

    const error = new Error(message);
    error.status = res.status;
    throw error;
  }

  // Handle 204 No Content
  if (res.status === 204) return null;

  return res.json();
}

// ---------------------------------------------------------------------------
// Legacy API functions (backward compatible)
// ---------------------------------------------------------------------------

export async function askQuestion(question, { signal } = {}) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* keep default message */
    }
    throw new Error(message);
  }

  const data = await res.json();
  return data.answer;
}

export async function checkHealth({ signal } = {}) {
  const res = await fetch(`${API_BASE}/health`, { signal });
  if (!res.ok) throw new Error(`Health check failed (${res.status})`);
  return res.json();
}

export default API_BASE;
