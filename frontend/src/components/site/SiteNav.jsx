/**
 * SiteNav — minimal top navigation for the landing page.
 * Brand + a single "Open Assistant" CTA. Everything else lives in the app.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext.jsx";
import ThemeToggle from "../ui/ThemeToggle.jsx";

export default function SiteNav() {
  const [scrolled, setScrolled] = useState(false);
  const { user, logout } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      setLoggingOut(false);
    }
  };

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled
          ? "border-b border-[var(--border-primary)] bg-[var(--surface-primary)]/95 shadow-sm backdrop-blur-md"
          : "bg-transparent"
      }`}
    >
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4 sm:px-6">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 shrink-0" aria-label="CHARUSAT AI Assistant home">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-primary)]/90">
            <svg viewBox="0 0 24 24" className="h-4.5 w-4.5 fill-white" aria-hidden>
              <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
            </svg>
          </span>
          <span className="text-[15px] font-semibold tracking-tight text-[var(--text-primary)]">
            CHARUSAT Assistant
          </span>
        </Link>

        {/* Section links */}
        <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-[var(--text-tertiary)]" aria-label="Main Navigation">
          <a href="#programmes" className="transition hover:text-[var(--text-primary)]">Programmes</a>
          <a href="#topics" className="transition hover:text-[var(--text-primary)]">Topics</a>
          <a href="#how-it-works" className="transition hover:text-[var(--text-primary)]">How It Works</a>
          <a href="#contacts" className="transition hover:text-[var(--text-primary)]">Helpline</a>
        </nav>

        {/* CTA + Auth + Theme */}
        <div className="flex items-center gap-2 sm:gap-3">
          <ThemeToggle />

          {user ? (
            <div className="flex items-center gap-2">
              <span
                className="hidden lg:inline-block max-w-[120px] truncate text-xs font-medium text-[var(--text-tertiary)]"
                title={user.email}
              >
                {user.name || user.email}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                disabled={loggingOut}
                className="inline-flex items-center rounded-lg border border-[var(--border-primary)] bg-[var(--surface-hover)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition hover:border-[var(--error-border)] hover:bg-[var(--error-surface)] hover:text-[var(--error)] disabled:opacity-50"
                aria-label="Log out"
              >
                {loggingOut ? "Signing out…" : "Log Out"}
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="inline-flex items-center rounded-lg border border-[var(--border-primary)] bg-[var(--surface-hover)] px-3 py-1.5 text-xs sm:text-sm font-medium text-[var(--text-secondary)] transition hover:border-[var(--border-hover)] hover:text-[var(--text-primary)]"
            >
              Log In
            </Link>
          )}

          <Link
            to="/chat"
            className="inline-flex items-center gap-1.5 sm:gap-2 rounded-lg bg-[var(--accent-primary)] px-3.5 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-medium text-white transition hover:bg-[var(--accent-primary-hover)] shrink-0"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
            <span>Open Assistant</span>
          </Link>
        </div>
      </div>
    </header>
  );
}