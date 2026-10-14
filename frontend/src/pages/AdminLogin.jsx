/**
 * AdminLogin — dedicated, secure login portal for administrators.
 * Calls /api/admin/login and redirects to /admin dashboard on success.
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";
import ThemeToggle from "../components/ui/ThemeToggle.jsx";

export default function AdminLogin() {
  const navigate = useNavigate();
  const { adminLogin } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError("Please enter both email and password.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      await adminLogin(email.trim(), password);
      navigate("/admin", { replace: true });
    } catch (err) {
      setError(err.message || "Failed to authenticate. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-[var(--surface-primary)] p-4 text-[var(--text-primary)]">
      {/* Corner theme toggle */}
      <div className="absolute right-4 top-4 z-20">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-sm rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-secondary)] p-8 shadow-xl">
        {/* Brand */}
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--accent-primary)]/15 ring-1 ring-[var(--accent-primary)]/30 text-[var(--accent-primary)]">
            <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <span className="mt-3 inline-block rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-500">
            Staff & Faculty Portal
          </span>
          <h1 className="mt-2 text-xl font-bold tracking-tight text-[var(--text-primary)]">
            Admin Authentication
          </h1>
          <p className="mt-1 text-xs text-[var(--text-tertiary)]">
            Sign in to manage system analytics and knowledge gaps.
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-5 rounded-xl border border-[var(--error-border)] bg-[var(--error-surface)] p-3 text-xs text-[var(--error)]" role="alert">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="admin-email" className="block text-xs font-medium text-[var(--text-secondary)]">
              Admin Email
            </label>
            <input
              id="admin-email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@charusat.ac.in"
              className="mt-1.5 w-full rounded-xl border border-[var(--border-primary)] bg-[var(--surface-primary)] px-3.5 py-2.5 text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--accent-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-primary)]"
            />
          </div>

          <div>
            <label htmlFor="admin-password" className="block text-xs font-medium text-[var(--text-secondary)]">
              Password
            </label>
            <input
              id="admin-password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1.5 w-full rounded-xl border border-[var(--border-primary)] bg-[var(--surface-primary)] px-3.5 py-2.5 text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--accent-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-primary)]"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-[var(--accent-primary)] py-2.5 text-xs font-semibold text-white shadow-md transition hover:bg-[var(--accent-primary-hover)] disabled:opacity-50"
          >
            {loading ? "Authenticating..." : "Sign In to Dashboard"}
          </button>
        </form>

        <div className="mt-6 text-center text-xs text-[var(--text-muted)]">
          <Link to="/" className="text-[var(--accent-primary)] hover:underline">
            Return to Homepage
          </Link>
        </div>
      </div>
    </div>
  );
}
