/**
 * WelcomeScreen - empty state for the chat page.
 * Plain scope statement, source disclosure, and 4 starter questions
 * taken from the real question bank as rectangular buttons.
 */
import { useEffect, useState } from "react";
import { getRandomStarterQuestions, loadQuestionBank } from "../../lib/questionBank.js";

export default function WelcomeScreen({ onSendPrompt, questionBank }) {
  const [starters, setStarters] = useState([]);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      const bank = questionBank || (await loadQuestionBank());
      if (!cancelled) {
        const picked = getRandomStarterQuestions(bank);
        setStarters(picked.slice(0, 4));
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [questionBank]);

  return (
    <div className="flex h-full flex-col items-center justify-center px-4 py-8 sm:py-12">
      <div className="w-full max-w-2xl text-center">
        {/* Wordmark */}
        <div className="mb-3 inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-medium" style={{ borderColor: "var(--border)", background: "var(--surface-2)", color: "var(--accent)" }}>
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor" aria-hidden="true">
            <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
          </svg>
          <span>CHARUSAT Online Programmes Assistant</span>
        </div>

        <h1 className="text-xl font-semibold tracking-tight sm:text-2xl" style={{ color: "var(--text)" }}>
          What would you like to know?
        </h1>

        <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
          Ask about fees, eligibility, syllabus, admissions and exams for the online BBA, BCA, MBA and MCA programmes.
        </p>

        <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
          Answers are grounded in official CHARUSAT programme documentation.
        </p>

        {/* 4 Starter Questions */}
        <div className="mt-6 grid grid-cols-1 gap-2.5 sm:grid-cols-2 text-left" role="group" aria-label="Sample questions">
          {starters.map((s) => (
            <button
              key={s.id}
              onClick={() => onSendPrompt(s.text)}
              className="flex items-start gap-2.5 rounded-lg border p-3.5 text-xs leading-relaxed transition hover:border-[var(--accent)] hover:bg-[var(--surface-hover)] cursor-pointer"
              style={{
                borderColor: "var(--border)",
                background: "var(--surface)",
                color: "var(--text)",
              }}
              type="button"
            >
              <svg
                className="mt-0.5 h-4 w-4 shrink-0"
                style={{ color: "var(--accent)" }}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
              >
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
              <span className="flex-1 font-normal">{s.text}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
