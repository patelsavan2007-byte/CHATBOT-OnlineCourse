/**
 * WelcomeScreen — empty state for the chat page.
 * Displays 4 FULL questions, from different categories, randomized on every visit
 * and different from the previous visit's set (stored in localStorage).
 */
import { useEffect, useState } from "react";
import { getRandomStarterQuestions, loadQuestionBank } from "../../lib/questionBank.js";

const CATEGORY_STYLES = {
  "General Questions": {
    icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253",
    color: "var(--accent)",
  },
  "Fees Related Questions": {
    icon: "M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z",
    color: "var(--tint-amber)",
  },
  "Admission Questions": {
    icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    color: "var(--tint-emerald)",
  },
  "Academic Questions": {
    icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4",
    color: "var(--tint-rose)",
  },
  "Technical Questions": {
    icon: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
    color: "var(--accent)",
  },
  "Career & Placement Questions": {
    icon: "M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
    color: "var(--tint-emerald)",
  },
  "Student Support Questions": {
    icon: "M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z",
    color: "var(--tint-amber)",
  },
};

export default function WelcomeScreen({ onSendPrompt, questionBank }) {
  const [starters, setStarters] = useState([]);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      const bank = questionBank || await loadQuestionBank();
      if (!cancelled) {
        const picked = getRandomStarterQuestions(bank);
        setStarters(picked);
      }
    }
    init();
    return () => { cancelled = true; };
  }, [questionBank]);

  return (
    <div className="flex h-full flex-col items-center justify-center px-4 py-12 sm:py-16">
      {/* Logo / Identity */}
      <div className="relative">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl" style={{ background: "var(--accent-surface)" }}>
          <svg viewBox="0 0 24 24" className="h-7 w-7 fill-[var(--accent-primary)]" aria-hidden>
            <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
          </svg>
        </div>
      </div>

      <h1
        className="mt-5 text-center text-2xl font-semibold sm:text-3xl"
        style={{ color: "var(--text-primary)" }}
      >
        CHARUSAT Assistant
      </h1>

      <p
        className="mt-3 max-w-md text-center text-sm leading-relaxed sm:text-base"
        style={{ color: "var(--text-tertiary)", animationDelay: "60ms" }}
      >
        Ask anything about CHARUSAT's online degree programmes - fees,
        eligibility, curriculum, admissions, and more.
      </p>

      {/* Suggestion grid */}
      <div
        className="mt-8 grid w-full max-w-xl grid-cols-1 gap-2.5 sm:grid-cols-2"
        style={{ animationDelay: "120ms" }}
      >
        {starters.map((s) => {
          const style = CATEGORY_STYLES[s.category] || CATEGORY_STYLES["General Questions"];
          return (
            <button
              key={s.id}
              onClick={() => onSendPrompt(s.text)}
              className="group flex items-start gap-3 rounded-xl border border-[var(--border-primary)] bg-[var(--surface-hover)] p-4 text-left text-[13px] transition hover:border-[var(--border-hover)] hover:bg-[var(--surface-active)] hover:shadow-sm"
              style={{ color: "var(--text-secondary)" }}
              type="button"
            >
              <svg
                className="mt-0.5 h-5 w-5 shrink-0 opacity-90 transition group-hover:opacity-100"
                style={{ color: style.color }}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
              >
                <path d={style.icon} />
              </svg>
              <span className="leading-snug transition group-hover:text-[var(--text-primary)]">
                {s.text}
              </span>
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <p
        className="mt-8 text-center text-[11px]"
        style={{ color: "var(--text-muted)", animationDelay: "180ms" }}
      >
        Answers are generated from CHARUSAT's official programme documents.
      </p>
    </div>
  );
}
