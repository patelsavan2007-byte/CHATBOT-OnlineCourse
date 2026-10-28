/**
 * App -- root routing for the CHARUSAT Online Programmes Assistant.
 *
 * Entry:        /  -> redirect to /chat
 * Auth:         /login  /signup
 * Application:  /chat  /chat/:conversationId  /settings
 * Info:         /about  /privacy  /terms
 * Admin:        /admin  (admin-only protected)  /admin/login
 */
import React, { Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext.jsx";

// Pages
import Login    from "./pages/Login.jsx";
import Signup   from "./pages/Signup.jsx";
import Chat     from "./pages/Chat.jsx";
import Settings from "./pages/Settings.jsx";

// Lazy pages
const Admin      = React.lazy(() => import("./pages/Admin.jsx"));
const AdminLogin = React.lazy(() => import("./pages/AdminLogin.jsx"));
const About      = React.lazy(() => import("./pages/About.jsx"));
const Privacy    = React.lazy(() => import("./pages/Privacy.jsx"));
const Terms      = React.lazy(() => import("./pages/Terms.jsx"));

// UI guards
import ErrorBoundary  from "./components/ui/ErrorBoundary.jsx";
import ProtectedRoute from "./components/auth/ProtectedRoute.jsx";

/* ---- Loading screen -- uses design tokens, no hard-coded dark ---- */
function AppLoader() {
  return (
    <div
      className="flex h-dvh items-center justify-center"
      style={{ background: "var(--page)", color: "var(--muted)" }}
    >
      <div className="flex flex-col items-center gap-3">
        <div
          className="flex h-9 w-9 items-center justify-center rounded-lg"
          style={{ background: "var(--accent-surface)" }}
        >
          <svg
            viewBox="0 0 24 24"
            className="h-5 w-5"
            style={{ fill: "var(--accent)" }}
            aria-hidden
          >
            <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
          </svg>
        </div>
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          Loading...
        </p>
      </div>
    </div>
  );
}

/* ---- 404 ---- */
function NotFound() {
  return (
    <div
      className="flex h-dvh flex-col items-center justify-center gap-4 px-4 text-center"
      style={{ background: "var(--page)" }}
    >
      <p
        className="text-8xl font-semibold leading-none"
        style={{ color: "var(--border-strong)" }}
      >
        404
      </p>
      <p className="text-base font-semibold" style={{ color: "var(--text)" }}>
        Page not found
      </p>
      <p className="max-w-xs text-sm" style={{ color: "var(--muted)" }}>
        The page you are looking for does not exist or has been moved.
      </p>
      <div className="mt-2 flex gap-3">
        <a
          href="/chat"
          className="rounded-lg px-5 py-2.5 text-sm font-medium transition hover:opacity-90"
          style={{
            background: "var(--accent)",
            color: "var(--accent-text)",
          }}
        >
          Open Assistant
        </a>
        <a
          href="/"
          className="rounded-lg border px-5 py-2.5 text-sm font-medium transition hover:opacity-80"
          style={{
            borderColor: "var(--border)",
            background: "var(--surface)",
            color: "var(--text-2)",
          }}
        >
          Home
        </a>
      </div>
    </div>
  );
}

export default function App() {
  const { loading } = useAuth();

  if (loading) return <AppLoader />;

  return (
    <ErrorBoundary>
      <Suspense fallback={<AppLoader />}>
        <Routes>
          {/* Entry -- redirect / to /chat */}
          <Route path="/" element={<Navigate to="/chat" replace />} />

          {/* Auth */}
          <Route path="/login"  element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* Chat -- accessible to guests and authenticated users */}
          <Route path="/chat"                  element={<Chat />} />
          <Route path="/chat/:conversationId"  element={<Chat />} />

          {/* Protected */}
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            }
          />

          {/* Admin */}
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute adminOnly>
                <Admin />
              </ProtectedRoute>
            }
          />

          {/* Info pages */}
          <Route path="/about"   element={<About />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms"   element={<Terms />} />

          {/* Legacy redirects */}
          <Route path="/history"        element={<Navigate to="/chat"     replace />} />
          <Route path="/profile"        element={<Navigate to="/settings" replace />} />
          <Route path="/programs"       element={<Navigate to="/chat"     replace />} />
          <Route path="/programs/:slug" element={<Navigate to="/chat"     replace />} />
          <Route path="/how-it-works"   element={<Navigate to="/about"    replace />} />
          <Route path="/faq"            element={<Navigate to="/chat"     replace />} />

          {/* 404 */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
