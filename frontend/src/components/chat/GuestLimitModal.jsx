/**
 * GuestLimitModal - restyled guest message limit dialog.
 * Plain backdrop, 8px card radius, standard design tokens.
 */
import { Link } from "react-router-dom";

export default function GuestLimitModal({ onClose }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="guest-limit-title"
    >
      {/* Plain backdrop overlay -- no backdrop blur */}
      <div
        className="fixed inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal card */}
      <div
        className="relative z-10 w-full max-w-sm rounded-lg border p-6 shadow-md"
        style={{
          borderColor: "var(--border)",
          background: "var(--surface)",
          color: "var(--text)",
        }}
      >
        {/* Dismiss button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 flex h-7 w-7 items-center justify-center rounded-md text-[var(--muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text)] cursor-pointer"
          aria-label="Dismiss"
          type="button"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>

        <h2 id="guest-limit-title" className="text-base font-semibold leading-snug">
          Guest message limit reached
        </h2>
        <p className="mt-2 text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
          Sign in or create a free account to continue asking questions and preserve your conversation history.
        </p>

        <div className="mt-5 flex flex-col gap-2">
          <Link
            to="/signup"
            className="flex items-center justify-center rounded-md px-3.5 py-2 text-xs font-medium text-white transition hover:opacity-90"
            style={{ background: "var(--accent)" }}
          >
            Create free account
          </Link>
          <Link
            to="/login"
            className="flex items-center justify-center rounded-md border px-3.5 py-2 text-xs font-medium transition hover:bg-[var(--surface-hover)]"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}
          >
            Sign in
          </Link>
          <button
            onClick={onClose}
            type="button"
            className="mt-1 text-center text-xs transition hover:underline cursor-pointer"
            style={{ color: "var(--muted)" }}
          >
            Stay on page
          </button>
        </div>
      </div>
    </div>
  );
}