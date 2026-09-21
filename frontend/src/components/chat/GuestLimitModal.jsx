/**
 * GuestLimitModal — shown when guest message limit is reached.
 * Clean, non-intrusive, offers clear path to sign up.
 */
import { Link } from "react-router-dom";

export default function GuestLimitModal({ onClose }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="guest-limit-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />

      {/* Panel */}
      <div className="relative w-full max-w-sm rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-secondary)] p-6 shadow-[var(--shadow-lg)] animate-fade-up">
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 flex h-7 w-7 items-center justify-center rounded-lg text-[var(--text-muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)]"
          aria-label="Dismiss"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>

        {/* Icon */}
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--border-primary)] bg-[var(--surface-hover)] text-[var(--accent-primary)] mb-4">
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        </div>

        <h2 id="guest-limit-title" className="text-base font-semibold text-[var(--text-primary)]">
          Create a free account to continue
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-[var(--text-tertiary)]">
          You've reached the guest message limit. Sign up for free to ask unlimited questions and save your conversation history.
        </p>

        <div className="mt-6 flex flex-col gap-2.5">
          <Link
            to="/signup"
            className="flex items-center justify-center gap-2 rounded-lg bg-[var(--accent-primary)] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--accent-primary-hover)]"
          >
            Create free account
          </Link>
          <Link
            to="/login"
            className="flex items-center justify-center gap-2 rounded-lg border border-[var(--border-primary)] bg-[var(--surface-hover)] px-4 py-2.5 text-sm font-medium text-[var(--text-secondary)] transition hover:bg-[var(--surface-active)]"
          >
            Sign in
          </Link>
          <button
            onClick={onClose}
            className="text-xs text-[var(--text-muted)] transition hover:text-[var(--text-tertiary)]"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}