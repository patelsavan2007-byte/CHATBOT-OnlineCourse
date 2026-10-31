import LogoLockup from "../components/ui/LogoLockup.jsx";
/**
 * Login page - clean, straightforward authentication form.
 * No marketing panels, no gradients, strict token styling.
 */
import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";
import GoogleButton from "../components/auth/GoogleButton.jsx";
import ThemeToggle from "../components/ui/ThemeToggle.jsx";

function EyeIcon({ open }) {
  return open ? (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  ) : (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
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

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
      setError(err.message || "Sign in failed. Please check your credentials.");
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
    <div
      className="relative flex min-h-dvh flex-col items-center justify-center p-4 font-sans"
      style={{ background: "var(--page)", color: "var(--text)" }}
    >
      <div className="absolute right-4 top-4 z-20">
        <ThemeToggle />
      </div>

      <div
        className="w-full max-w-sm rounded-lg border p-6 sm:p-8"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <div className="mb-6 text-center">
          <div className="flex justify-center mb-4">
            <Link to="/chat" aria-label="CCOE CHARUSAT home">
              <LogoLockup height={36} />
            </Link>
          </div>
          <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text)" }}>
            Sign in
          </h1>
          <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
            Center for Online Education (CCOE), CHARUSAT
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="mb-4 rounded-md border p-3 text-xs"
            style={{
              borderColor: "var(--danger)",
              background: "var(--surface-2)",
              color: "var(--danger)",
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="login-email" className="mb-1 block text-xs font-medium" style={{ color: "var(--text-2)" }}>
              Email address
            </label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              required
              autoComplete="email"
              className="w-full rounded-lg border px-3 py-2 text-xs focus:outline-none"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border)",
                color: "var(--text)",
              }}
            />
          </div>

          <div>
            <label htmlFor="login-password" className="mb-1 block text-xs font-medium" style={{ color: "var(--text-2)" }}>
              Password
            </label>
            <div className="relative">
              <input
                id="login-password"
                type={showPass ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                required
                autoComplete="current-password"
                className="w-full rounded-lg border px-3 py-2 pr-9 text-xs focus:outline-none"
                style={{
                  background: "var(--surface)",
                  borderColor: "var(--border)",
                  color: "var(--text)",
                }}
              />
              <button
                type="button"
                onClick={() => setShowPass((v) => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 transition"
                style={{ color: "var(--muted)" }}
                aria-label={showPass ? "Hide password" : "Show password"}
              >
                <EyeIcon open={showPass} />
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !email.trim() || !password}
            className="flex w-full items-center justify-center gap-2 rounded-md px-4 py-2 text-xs font-medium text-white transition hover:opacity-90 disabled:opacity-50"
            style={{ background: "var(--accent)" }}
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="my-4 flex items-center gap-3">
          <div className="h-px flex-1" style={{ background: "var(--border)" }} />
          <span className="text-[11px]" style={{ color: "var(--muted)" }}>or</span>
          <div className="h-px flex-1" style={{ background: "var(--border)" }} />
        </div>

        <GoogleButton onCredential={handleGoogle} disabled={loading} label="Sign in with Google" />

        <div className="mt-6 text-center text-xs space-y-2" style={{ color: "var(--muted)" }}>
          <p>
            Don't have an account?{" "}
            <Link to="/signup" className="font-medium underline" style={{ color: "var(--accent)" }}>
              Create one
            </Link>
          </p>
          <p>
            <Link to="/chat" className="hover:underline" style={{ color: "var(--text-2)" }}>
              Continue as guest
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
