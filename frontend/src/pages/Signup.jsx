/**
 * Signup page - clean user registration form.
 * No marketing panels, includes Terms and Privacy consent link.
 */
import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
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

function PasswordStrength({ password }) {
  const checks = [
    { label: "8+ chars", ok: password.length >= 8 },
    { label: "Uppercase", ok: /[A-Z]/.test(password) },
    { label: "Number", ok: /\d/.test(password) },
  ];
  if (!password) return null;
  return (
    <div className="mt-1.5 flex gap-2">
      {checks.map(({ label, ok }) => (
        <div key={label} className="flex flex-1 flex-col gap-0.5">
          <div
            className="h-1 rounded-sm"
            style={{ background: ok ? "var(--success)" : "var(--border)" }}
          />
          <span className="text-[10px]" style={{ color: ok ? "var(--success)" : "var(--muted)" }}>
            {label}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function Signup() {
  const { signup, googleLogin, user } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [showConf, setShowConf] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user) navigate("/chat", { replace: true });
  }, [user, navigate]);

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
    if (err) {
      setError(err);
      return;
    }
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
          <Link
            to="/chat"
            className="inline-flex items-center gap-2 mb-3"
            aria-label="CHARUSAT Assistant home"
          >
            <span
              className="flex h-8 w-8 items-center justify-center rounded-md"
              style={{ background: "var(--accent-surface)", color: "var(--accent)" }}
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden="true">
                <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
              </svg>
            </span>
            <span className="text-sm font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              CHARUSAT Assistant
            </span>
          </Link>
          <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text)" }}>
            Create account
          </h1>
          <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
            Register to save and sync your conversation history
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

        <form onSubmit={handleSubmit} className="space-y-3.5" noValidate>
          <div>
            <label htmlFor="signup-name" className="mb-1 block text-xs font-medium" style={{ color: "var(--text-2)" }}>
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
              className="w-full rounded-lg border px-3 py-2 text-xs focus:outline-none"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border)",
                color: "var(--text)",
              }}
            />
          </div>

          <div>
            <label htmlFor="signup-email" className="mb-1 block text-xs font-medium" style={{ color: "var(--text-2)" }}>
              Email address
            </label>
            <input
              id="signup-email"
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
            <label htmlFor="signup-password" className="mb-1 block text-xs font-medium" style={{ color: "var(--text-2)" }}>
              Password
            </label>
            <div className="relative">
              <input
                id="signup-password"
                type={showPass ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                required
                autoComplete="new-password"
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
            <PasswordStrength password={password} />
          </div>

          <div>
            <label htmlFor="signup-confirm" className="mb-1 block text-xs font-medium" style={{ color: "var(--text-2)" }}>
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
                className="w-full rounded-lg border px-3 py-2 pr-9 text-xs focus:outline-none"
                style={{
                  background: "var(--surface)",
                  borderColor: confirm && confirm !== password ? "var(--danger)" : "var(--border)",
                  color: "var(--text)",
                }}
              />
              <button
                type="button"
                onClick={() => setShowConf((v) => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 transition"
                style={{ color: "var(--muted)" }}
                aria-label={showConf ? "Hide password" : "Show password"}
              >
                <EyeIcon open={showConf} />
              </button>
            </div>
          </div>

          {/* Consent line */}
          <p className="text-[11px] leading-relaxed" style={{ color: "var(--muted)" }}>
            By creating an account, you agree to our{" "}
            <Link to="/terms" className="underline" style={{ color: "var(--accent)" }}>
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link to="/privacy" className="underline" style={{ color: "var(--accent)" }}>
              Privacy Policy
            </Link>.
          </p>

          <button
            type="submit"
            disabled={loading || !name.trim() || !email.trim() || !password || !confirm}
            className="flex w-full items-center justify-center gap-2 rounded-md px-4 py-2 text-xs font-medium text-white transition hover:opacity-90 disabled:opacity-50"
            style={{ background: "var(--accent)" }}
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <div className="my-4 flex items-center gap-3">
          <div className="h-px flex-1" style={{ background: "var(--border)" }} />
          <span className="text-[11px]" style={{ color: "var(--muted)" }}>or</span>
          <div className="h-px flex-1" style={{ background: "var(--border)" }} />
        </div>

        <GoogleButton onCredential={handleGoogle} disabled={loading} label="Sign up with Google" />

        <div className="mt-6 text-center text-xs space-y-2" style={{ color: "var(--muted)" }}>
          <p>
            Already have an account?{" "}
            <Link to="/login" className="font-medium underline" style={{ color: "var(--accent)" }}>
              Sign in
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
