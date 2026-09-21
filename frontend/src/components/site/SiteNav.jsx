/**
 * SiteNav — minimal top navigation for the landing page.
 * Brand + a single "Open Assistant" CTA. Everything else lives in the app.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext.jsx";

export default function SiteNav() {
  const [scrolled, setScrolled] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

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

        {/* CTA */}
        <div className="flex items-center gap-3">
          {!user && (
            <Link
              to="/login"
              className="hidden text-sm font-medium text-[var(--text-tertiary)] transition hover:text-[var(--text-primary)] sm:inline-block"
            >
              Sign In
            </Link>
          )}
          <Link
            to="/chat"
            className="inline-flex items-center gap-2 rounded-lg bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition hover:bg-[var(--accent-primary-hover)]"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
            Open Assistant
          </Link>
        </div>
      </div>
    </header>
  );
}