/**
 * Login page — clean, professional auth form.
 * Part of the same product, not a generic Firebase template.
 */
import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";
import GoogleButton from "../components/auth/GoogleButton.jsx";

function EyeIcon({ open }) {
  return open ? (
    <svg className="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  ) : (
    <svg className="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export default function Login() {
  const { login, googleLogin, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/chat";

  const [email, setEmail]           = useState("");
  const [password, setPassword]     = useState("");
  const [showPass, setShowPass]     = useState(false);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");

  useEffect(() => {
    if (user) navigate(from, { replace: true });
  }, [user, navigate, from]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setLoading(true);
    setError("");
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Sign in failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async (credential) => {
    setLoading(true);
    setError("");
    try {
      await googleLogin(credential);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Google sign-in failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-dvh bg-slate-950">
      {/* Left panel — branding */}
      <div className="hidden w-[420px] shrink-0 flex-col justify-between bg-slate-900 border-r border-white/5 px-10 py-12 lg:flex">
        <Link to="/" className="inline-flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800">
            <svg viewBox="0 0 24 24" className="h-4.5 w-4.5 fill-indigo-400" aria-hidden>
              <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
            </svg>
          </span>
          <span className="text-sm font-semibold text-white">CHARUSAT Online</span>
        </Link>

        <div>
          <blockquote className="font-display text-2xl font-normal leading-snug text-white">
            "Access official programme information anytime — fees, eligibility, curriculum, and more."
          </blockquote>
          <p className="mt-6 text-sm text-slate-500">
            Sign in to save your conversations and pick up where you left off.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {["NAAC A+", "UGC Recognised", "NIRF Top 200"].map((a) => (
            <span key={a} className="rounded-md border border-white/8 bg-white/4 px-2.5 py-1 text-[11px] text-slate-500">
              {a}
            </span>
          ))}
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex flex-1 flex-col items-center justify-center px-4 py-12 sm:px-6">
        {/* Mobile logo */}
        <div className="mb-8 lg:hidden">
          <Link to="/" className="inline-flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800">
              <svg viewBox="0 0 24 24" className="h-4.5 w-4.5 fill-indigo-400" aria-hidden>
                <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
              </svg>
            </span>
            <span className="text-sm font-semibold text-white">CHARUSAT Online</span>
          </Link>
        </div>

        <div className="w-full max-w-[380px]">
          <div className="mb-8">
            <h1 className="text-2xl font-semibold text-white">Sign in</h1>
            <p className="mt-1.5 text-sm text-slate-400">
              Don't have an account?{" "}
              <Link to="/signup" className="font-medium text-indigo-400 transition hover:text-indigo-300">
                Create one
              </Link>
            </p>
          </div>

          {/* Error */}
          {error && (
            <div role="alert" className="mb-5 flex items-start gap-2.5 rounded-lg border border-rose-500/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
              <svg className="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label htmlFor="login-email" className="mb-1.5 block text-xs font-medium text-slate-400">
                Email address
              </label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
                className="w-full rounded-lg border border-white/8 bg-white/5 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-600 outline-none transition focus:border-indigo-500/60 focus:bg-white/8 focus:ring-2 focus:ring-indigo-500/15"
              />
            </div>

            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label htmlFor="login-password" className="text-xs font-medium text-slate-400">
                  Password
                </label>
                <button
                  type="button"
                  className="text-xs text-slate-600 transition hover:text-slate-400"
                  onClick={() => {/* forgot password — placeholder */}}
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPass ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                  className="w-full rounded-lg border border-white/8 bg-white/5 px-3.5 py-2.5 pr-10 text-sm text-white placeholder:text-slate-600 outline-none transition focus:border-indigo-500/60 focus:bg-white/8 focus:ring-2 focus:ring-indigo-500/15"
                />
                <button
                  type="button"
                  onClick={() => setShowPass((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-slate-300"
                  aria-label={showPass ? "Hide password" : "Show password"}
                >
                  <EyeIcon open={showPass} />
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !email.trim() || !password}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-400 border-t-slate-900" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-white/8" />
            <span className="text-xs text-slate-600">or</span>
            <div className="h-px flex-1 bg-white/8" />
          </div>

          {/* Google */}
          <GoogleButton onCredential={handleGoogle} disabled={loading} label="Continue with Google" />

          {/* Back */}
          <p className="mt-8 text-center">
            <Link to="/" className="text-xs text-slate-700 transition hover:text-slate-500">
              ← Back to home
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
