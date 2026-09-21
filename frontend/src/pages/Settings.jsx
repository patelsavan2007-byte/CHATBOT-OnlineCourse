/**
 * Settings page — clean account management for authenticated users.
 */
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3.5 border-b border-[var(--border-primary)] last:border-0">
      <dt className="text-sm text-[var(--text-tertiary)]">{label}</dt>
      <dd className="text-sm font-medium text-[var(--text-primary)] text-right">{value}</dd>
    </div>
  );
}

export default function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="min-h-dvh bg-[var(--surface-primary)]">
      {/* Header */}
      <header className="border-b border-[var(--border-primary)] bg-[var(--surface-primary)]/90 px-4 py-3.5 backdrop-blur-sm">
        <div className="mx-auto flex max-w-2xl items-center gap-3">
          <Link
            to="/chat"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)]"
            aria-label="Back to chat"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M19 12H5M12 5l-7 7 7 7" />
            </svg>
          </Link>
          <h1 className="text-[15px] font-semibold text-[var(--text-primary)]">Account Settings</h1>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        {user ? (
          <div className="space-y-5">
            {/* Profile card */}
            <section aria-labelledby="profile-heading" className="rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-secondary)] p-6">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-[var(--accent-primary)] text-xl font-semibold text-white shadow-inner">
                  {(user.name?.[0] || user.email?.[0] || "U").toUpperCase()}
                </div>
                <div>
                  <p className="text-lg font-medium text-[var(--text-primary)]">{user.name || "User"}</p>
                  <p className="text-sm text-[var(--text-tertiary)]">{user.email}</p>
                  <span className="mt-1 inline-block rounded-full border border-[var(--accent-primary)]/30 bg-[var(--accent-surface)] px-2.5 py-0.5 text-xs font-medium text-[var(--accent-primary-hover)]">
                    {user.role}
                  </span>
                </div>
              </div>
            </section>

            {/* Account details */}
            <section aria-labelledby="account-heading" className="rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-secondary)] p-6">
              <h2 id="account-heading" className="mb-2 text-xs font-semibold uppercase tracking-widest text-[var(--text-muted)]">
                Account
              </h2>
              <dl>
                <InfoRow label="Name"       value={user.name || "—"} />
                <InfoRow label="Email"      value={user.email} />
                <InfoRow label="Role"       value={user.role} />
                <InfoRow label="Sign-in method" value={user.google_id ? "Google" : "Email & Password"} />
              </dl>
            </section>

            {/* Navigation */}
            <section className="rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-secondary)] p-4">
              <nav className="flex flex-col gap-1">
                <Link
                  to="/chat"
                  className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-[var(--text-secondary)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                  </svg>
                  Open Assistant
                </Link>
                {user.role === "admin" && (
                  <Link
                    to="/admin"
                    className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-amber-600 transition hover:bg-amber-500/10 dark:text-amber-500 dark:hover:bg-amber-500/8"
                  >
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                    Admin Dashboard
                  </Link>
                )}
              </nav>
            </section>

            {/* Danger zone */}
            <section className="rounded-2xl border border-[var(--error-border)] bg-[var(--error-surface)] p-6">
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-[var(--error)]">
                Sign out
              </h2>
              <p className="mb-4 text-sm text-[var(--text-tertiary)]">
                You'll need to sign in again to access your saved conversations.
              </p>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 rounded-lg border border-[var(--error-border)] bg-[var(--error-surface)] px-4 py-2.5 text-sm font-medium text-[var(--error)] transition hover:opacity-80"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
                </svg>
                Sign out
              </button>
            </section>
          </div>
        ) : (
          <div className="rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-secondary)] px-8 py-12 text-center">
            <p className="text-sm text-[var(--text-tertiary)]">You're not signed in.</p>
            <Link to="/login" className="mt-4 inline-flex items-center gap-2 rounded-lg bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition hover:bg-[var(--accent-primary-hover)]">
              Sign in
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
