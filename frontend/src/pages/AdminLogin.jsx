import LogoLockup from "../components/ui/LogoLockup.jsx";
/**
 * AdminLogin - dedicated staff authentication portal for administrators.
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
          <span
            className="rounded border px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase"
            style={{
              borderColor: "var(--border)",
              background: "var(--surface-2)",
              color: "var(--accent)",
            }}
          >
            Staff Portal
          </span>
          <h1 className="mt-2 text-xl font-bold tracking-tight" style={{ color: "var(--text)" }}>
            Admin Console Login
          </h1>
          <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
            Sign in with an authorized administrator account
          </p>
        </div>

        {error && (
          <div
            className="mb-4 rounded-md border p-3 text-xs"
            style={{
              borderColor: "var(--danger)",
              background: "var(--surface-2)",
              color: "var(--danger)",
            }}
            role="alert"
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="admin-email" className="block text-xs font-medium mb-1" style={{ color: "var(--text-2)" }}>
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
              className="w-full rounded-lg border px-3 py-2 text-xs focus:outline-none"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border)",
                color: "var(--text)",
              }}
            />
          </div>

          <div>
            <label htmlFor="admin-password" className="block text-xs font-medium mb-1" style={{ color: "var(--text-2)" }}>
              Password
            </label>
            <input
              id="admin-password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              className="w-full rounded-lg border px-3 py-2 text-xs focus:outline-none"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border)",
                color: "var(--text)",
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !email.trim() || !password}
            className="w-full rounded-md px-4 py-2 text-xs font-medium text-white transition hover:opacity-90 disabled:opacity-50"
            style={{ background: "var(--accent)" }}
          >
            {loading ? "Authenticating..." : "Sign in to console"}
          </button>
        </form>

        <div className="mt-6 text-center text-xs" style={{ color: "var(--muted)" }}>
          <Link to="/chat" className="hover:underline" style={{ color: "var(--text-2)" }}>
            Return to chat
          </Link>
        </div>
      </div>
    </div>
  );
}
