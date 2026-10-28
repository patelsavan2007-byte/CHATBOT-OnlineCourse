/**
 * Signup page — matching the Login design system.
 */
import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";
import GoogleButton from "../components/auth/GoogleButton.jsx";
import ThemeToggle from "../components/ui/ThemeToggle.jsx";

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

function PasswordStrength({ password }) {
  const checks = [
    { label: "8+ characters", ok: password.length >= 8 },
    { label: "Uppercase letter", ok: /[A-Z]/.test(password) },
    { label: "Number", ok: /\d/.test(password) },
  ];
  if (!password) return null;
  return (
    <div className="mt-2 flex gap-2">
      {checks.map(({ label, ok }) => (
        <div key={label} className="flex flex-1 flex-col gap-1">
          <div className={`h-0.5 rounded-sm transition ${ok ? "bg-emerald-500" : "bg-[var(--border)]"}`} />
          <span className={`text-[10px] ${ok ? "text-emerald-500" : "text-[var(--text-muted)]"}`}>{label}</span>
        </div>
      ))}
    </div>
  );
}

export default function Signup() {
  const { signup, googleLogin, user } = useAuth();
  const navigate = useNavigate();

  const [name, setName]           = useState("");
  const [email, setEmail]         = useState("");
  const [password, setPassword]   = useState("");
  const [confirm, setConfirm]     = useState("");
  const [showPass, setShowPass]   = useState(false);
  const [showConf, setShowConf]   = useState(false);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");

  useEffect(() => { if (user) navigate("/chat", { replace: true }); }, [user, navigate]);

  const validate = () => {
    if (!name.trim()) return "Please enter your name.";
    if (!email.trim()) return "Please enter your email.";
    if (password.length < 8) return "Password must be at least 8 characters.";
    if (password !== confirm) return "Passwords do not match.";
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const err = validate();
    if (err) { setError(err); return; }
    setLoading(true);
    setError("");
    try {
      await signup(name.trim(), email.trim(), password);
      navigate("/chat", { replace: true });
    } catch (err) {
      setError(err.message || "Account creation failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async (credential) => {
    setLoading(true);
    setError("");
    try {
      await googleLogin(credential);
      navigate("/chat", { replace: true });
    } catch (err) {
      setError(err.message || "Google sign-up failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-dvh bg-[var(--surface-primary)] text-[var(--text-primary)]">
      {/* Corner theme toggle */}
      <div className="absolute right-4 top-4 z-20">
        <ThemeToggle />
      </div>

      {/* Left panel */}
      <div className="hidden w-[420px] shrink-0 flex-col justify-between bg-[var(--surface-secondary)] border-r border-[var(--border-primary)] px-10 py-12 lg:flex">
        <Link to="/" className="inline-flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] ring-1 ring-[var(--accent-primary)]/30">
            <svg viewBox="0 0 24 24" className="h-4.5 w-4.5 fill-current" aria-hidden>
              <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
            </svg>
          </span>
          <span className="text-sm font-semibold text-[var(--text-primary)]">CHARUSAT Online</span>
        </Link>

        <div className="space-y-5">
          {[
            { icon: "M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z", text: "Conversations saved to your account" },
            { icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z", text: "Pick up where you left off, any time" },
            { icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z", text: "Free to create and use" },
          ].map(({ icon, text }) => (
            <div key={text} className="flex items-center gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--border-primary)] bg-[var(--surface-hover)] text-[var(--accent-primary)]">
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
                  <path d={icon} />
                </svg>
              </div>
              <span className="text-sm text-[var(--text-secondary)]">{text}</span>
            </div>
          ))}
        </div>

        <p className="text-xs text-[var(--text-muted)]">
          Already have an account?{" "}
          <Link to="/login" className="text-[var(--accent-primary)] hover:underline transition">
            Sign in →
          </Link>
        </p>
      </div>

      {/* Right panel — form */}
      <div className="flex flex-1 flex-col items-center justify-center px-4 py-12 sm:px-6">
        {/* Mobile logo */}
        <div className="mb-8 lg:hidden">
          <Link to="/" className="inline-flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] ring-1 ring-[var(--accent-primary)]/30">
              <svg viewBox="0 0 24 24" className="h-4.5 w-4.5 fill-current" aria-hidden>
                <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
              </svg>
            </span>
            <span className="text-sm font-semibold text-[var(--text-primary)]">CHARUSAT Online</span>
          </Link>
        </div>

        <div className="w-full max-w-[380px]">
          <div className="mb-8">
            <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Create account</h1>
            <p className="mt-1.5 text-sm text-[var(--text-tertiary)]">
              Already have an account?{" "}
              <Link to="/login" className="font-medium text-[var(--accent-primary)] transition hover:text-[var(--accent-primary-hover)]">
                Sign in
              </Link>
            </p>
          </div>

          {/* Error */}
          {error && (
            <div role="alert" className="mb-5 flex items-start gap-2.5 rounded-lg border border-[var(--error-border)] bg-[var(--error-surface)] px-4 py-3 text-sm text-[var(--error)]">
              <svg className="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {/* Name */}
            <div>
              <label htmlFor="signup-name" className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                Full name
              </label>
              <input
                id="signup-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                required
                autoComplete="name"
                className="w-full rounded-lg border border-[var(--border-primary)] bg-[var(--surface-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition focus:border-[var(--accent-primary)] focus:ring-2 focus:ring-[var(--accent-primary)]/20"
              />
            </div>

            {/* Email */}
            <div>
              <label htmlFor="signup-email" className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                Email address
              </label>
              <input
                id="signup-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
                className="w-full rounded-lg border border-[var(--border-primary)] bg-[var(--surface-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition focus:border-[var(--accent-primary)] focus:ring-2 focus:ring-[var(--accent-primary)]/20"
              />
            </div>

            {/* Password */}
            <div>
              <label htmlFor="signup-password" className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                Password
              </label>
              <div className="relative">
                <input
                  id="signup-password"
                  type={showPass ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  required
                  autoComplete="new-password"
                  className="w-full rounded-lg border border-[var(--border-primary)] bg-[var(--surface-primary)] px-3.5 py-2.5 pr-10 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition focus:border-[var(--accent-primary)] focus:ring-2 focus:ring-[var(--accent-primary)]/20"
                />
                <button
                  type="button"
                  onClick={() => setShowPass((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
                  aria-label={showPass ? "Hide password" : "Show password"}
                >
                  <EyeIcon open={showPass} />
                </button>
              </div>
              <PasswordStrength password={password} />
            </div>

            {/* Confirm password */}
            <div>
              <label htmlFor="signup-confirm" className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                Confirm password
              </label>
              <div className="relative">
                <input
                  id="signup-confirm"
                  type={showConf ? "text" : "password"}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Repeat password"
                  required
                  autoComplete="new-password"
                  className={`w-full rounded-lg border bg-[var(--surface-primary)] px-3.5 py-2.5 pr-10 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition focus:ring-2 focus:ring-[var(--accent-primary)]/20 ${
                    confirm && confirm !== password
                      ? "border-[var(--error-border)] focus:border-[var(--error)]"
                      : "border-[var(--border-primary)] focus:border-[var(--accent-primary)]"
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowConf((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
                  aria-label={showConf ? "Hide confirm password" : "Show confirm password"}
                >
                  <EyeIcon open={showConf} />
                </button>
              </div>
              {confirm && confirm !== password && (
                <p className="mt-1.5 text-xs text-[var(--error)]">Passwords do not match</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || !name.trim() || !email.trim() || !password || !confirm}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--accent-primary)] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--accent-primary-hover)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" aria-hidden /> {/* allow-round: spinner */}
                  Creating account...
                </>
              ) : (
                "Create account"
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-[var(--border-primary)]" />
            <span className="text-xs text-[var(--text-muted)]">or</span>
            <div className="h-px flex-1 bg-[var(--border-primary)]" />
          </div>

          <GoogleButton onCredential={handleGoogle} disabled={loading} label="Sign up with Google" />

          <p className="mt-8 text-center">
            <Link to="/" className="text-xs text-[var(--text-muted)] transition hover:text-[var(--text-primary)]">
              ← Back to home
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
