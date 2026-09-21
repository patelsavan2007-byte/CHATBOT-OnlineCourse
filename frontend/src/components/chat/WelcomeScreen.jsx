/**
 * WelcomeScreen — empty state for the chat page.
 * Polished AI product feel. Warm greeting, categorized suggestions.
 */

const SUGGESTIONS = [
  {
    label: "What online programs are available?",
    icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253",
    color: "var(--tint-indigo)",
  },
  {
    label: "What is the eligibility for Online MCA?",
    icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    color: "var(--tint-emerald)",
  },
  {
    label: "What is the BBA fee structure?",
    icon: "M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z",
    color: "var(--tint-amber)",
  },
  {
    label: "How does the admission process work?",
    icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4",
    color: "var(--tint-rose)",
  },
];

export default function WelcomeScreen({ onSendPrompt }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-4 py-12 sm:py-16">
      {/* Logo / Identity */}
      <div className="relative">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--accent-surface)] animate-glow">
          <svg viewBox="0 0 24 24" className="h-7 w-7 fill-[var(--accent-primary)]" aria-hidden>
            <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
          </svg>
        </div>
      </div>

      <h1
        className="mt-5 text-center text-2xl font-semibold sm:text-3xl animate-fade-up"
        style={{ color: "var(--text-primary)" }}
      >
        CHARUSAT Assistant
      </h1>

      <p
        className="mt-3 max-w-md text-center text-sm leading-relaxed sm:text-base animate-fade-up"
        style={{ color: "var(--text-tertiary)", animationDelay: "60ms" }}
      >
        Ask me anything about CHARUSAT's online degree programmes — fees,
        eligibility, curriculum, admissions, and more.
      </p>

      {/* Suggestion grid */}
      <div
        className="mt-8 grid w-full max-w-xl grid-cols-1 gap-2.5 sm:grid-cols-2 animate-fade-up"
        style={{ animationDelay: "120ms" }}
      >
        {SUGGESTIONS.map((s) => (
          <button
            key={s.label}
            onClick={() => onSendPrompt(s.label)}
            className="group flex items-start gap-3 rounded-xl border border-[var(--border-primary)] bg-[var(--surface-hover)] p-4 text-left text-[13px] transition hover:border-[var(--border-hover)] hover:bg-[var(--surface-active)] hover:shadow-sm"
            style={{ color: "var(--text-secondary)" }}
          >
            <svg
              className="mt-0.5 h-5 w-5 shrink-0 opacity-90 transition group-hover:opacity-100"
              style={{ color: s.color }}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <path d={s.icon} />
            </svg>
            <span className="leading-snug transition group-hover:text-[var(--text-primary)]">
              {s.label}
            </span>
          </button>
        ))}
      </div>

      {/* Footer */}
      <p
        className="mt-8 text-center text-[11px] animate-fade-up"
        style={{ color: "var(--text-muted)", animationDelay: "180ms" }}
      >
        Answers are generated from CHARUSAT's official programme documents.
      </p>
    </div>
  );
}
