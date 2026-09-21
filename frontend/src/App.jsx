/**
 * App — root routing for the CHARUSAT AI Assistant.
 *
 * Entry / marketing:  /
 * Auth:               /login  /signup
 * Application:        /chat  /chat/:conversationId  /settings
 * Admin:              /admin  (protected, adminOnly)
 */
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext.jsx";

// Pages
import Landing       from "./pages/Landing.jsx";
import Login         from "./pages/Login.jsx";
import Signup        from "./pages/Signup.jsx";
import Chat          from "./pages/Chat.jsx";
import Settings      from "./pages/Settings.jsx";
import Admin         from "./pages/Admin.jsx";

// Auth guard
import ProtectedRoute from "./components/auth/ProtectedRoute.jsx";

/* ---- Loading screen ---- */
function AppLoader() {
  return (
    <div className="flex h-dvh items-center justify-center bg-slate-950">
      <div className="flex flex-col items-center gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900">
          <svg viewBox="0 0 24 24" className="h-5 w-5 fill-indigo-400 animate-pulse" aria-hidden>
            <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
          </svg>
        </div>
        <p className="text-xs text-slate-600">Loading…</p>
      </div>
    </div>
  );
}

/* ---- 404 ---- */
function NotFound() {
  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-4 bg-slate-950 px-4 text-center">
      <div className="font-display text-7xl font-normal text-slate-800">404</div>
      <p className="text-base font-medium text-slate-400">Page not found</p>
      <p className="max-w-xs text-sm text-slate-600">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <div className="flex gap-3 mt-2">
        <a
          href="/"
          className="rounded-lg bg-white px-5 py-2.5 text-sm font-medium text-slate-900 transition hover:bg-slate-100"
        >
          Go home
        </a>
        <a
          href="/chat"
          className="rounded-lg border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/10"
        >
          Open Assistant
        </a>
      </div>
    </div>
  );
}

export default function App() {
  const { loading } = useAuth();

  if (loading) return <AppLoader />;

  return (
    <Routes>
      {/* ---- Entry / landing ---- */}
      <Route path="/"              element={<Landing />} />

      {/* ---- Auth ---- */}
      <Route path="/login"  element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      {/* ---- Chat application — accessible to guests + authenticated ---- */}
      <Route path="/chat"                  element={<Chat />} />
      <Route path="/chat/:conversationId"  element={<Chat />} />

      {/* ---- Protected ---- */}
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute adminOnly>
            <Admin />
          </ProtectedRoute>
        }
      />

      {/* Legacy redirects */}
      <Route path="/about"    element={<Navigate to="/" replace />} />
      <Route path="/history"  element={<Navigate to="/chat" replace />} />
      <Route path="/profile"  element={<Navigate to="/settings" replace />} />
      <Route path="/programs" element={<Navigate to="/chat" replace />} />
      <Route path="/programs/:slug" element={<Navigate to="/chat" replace />} />
      <Route path="/how-it-works" element={<Navigate to="/chat" replace />} />
      <Route path="/faq"      element={<Navigate to="/chat" replace />} />

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
