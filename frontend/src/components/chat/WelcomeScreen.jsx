/**
 * WelcomeScreen - empty state for the chat page.
 * Plain scope statement, source disclosure, and 4 starter questions
 * taken from validated question bank entries as rectangular buttons.
 */
import { useEffect, useState } from "react";
import ThemedLogo from "../ui/ThemedLogo.jsx";
import { useAuth } from "../../contexts/AuthContext.jsx";
import { loadQuestionBank } from "../../lib/questionBank.js";
import { pickGreeting, pickDiverseStarters } from "../../lib/welcomeHelper.js";
import validatedStarterIds from "../../data/validated_starters.json";

const GREETING_STORAGE_KEY = "ccoe_last_greeting_idx";
const RECENT_STARTERS_KEY = "ccoe_recent_starters";

export default function WelcomeScreen({ onSendPrompt, questionBank }) {
  const { user } = useAuth();
  const [greeting, setGreeting] = useState("What would you like to know?");
  const [starters, setStarters] = useState([]);

  useEffect(() => {
    // 1. Pick non-repeating greeting
    try {
      const storedIdx = sessionStorage.getItem(GREETING_STORAGE_KEY);
      const { greeting: chosenGreeting, index } = pickGreeting(user, storedIdx);
      setGreeting(chosenGreeting);
      sessionStorage.setItem(GREETING_STORAGE_KEY, String(index));
    } catch {
      setGreeting(user ? "Welcome" : "What would you like to know?");
    }
  }, [user]);

  useEffect(() => {
    let cancelled = false;

    async function initStarters() {
      const bank = questionBank || (await loadQuestionBank());
      if (cancelled) return;

      let recentIds = [];
      try {
        const rawRecent = sessionStorage.getItem(RECENT_STARTERS_KEY);
        if (rawRecent) recentIds = JSON.parse(rawRecent);
      } catch {
        recentIds = [];
      }

      const picked = pickDiverseStarters(bank, validatedStarterIds, recentIds, 4);
      if (!cancelled && picked.length > 0) {
        setStarters(picked);
        try {
          const newRecent = picked.map((p) => p.id);
          sessionStorage.setItem(RECENT_STARTERS_KEY, JSON.stringify(newRecent));
        } catch {
          // sessionStorage quota or disabled
        }
      }
    }

    initStarters();
    return () => {
      cancelled = true;
    };
  }, [questionBank]);

  return (
    <div className="flex h-full flex-col items-center justify-center px-4 py-8 sm:py-12">
      <div className="w-full max-w-2xl text-center">
        {/* CCOE Logo */}
        <div className="mb-4 flex justify-center">
          <ThemedLogo variant="ccoe" height={40} alt="Center for Online Education" />
        </div>

        {/* Heading: 28-32px, normal weight */}
        <h1
          className="text-2xl sm:text-3xl font-normal tracking-tight"
          style={{ color: "var(--text)" }}
        >
          {greeting}
        </h1>

        <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
          Ask about fees, eligibility, syllabus, admissions and exams for the online BBA, BCA, MBA and MCA programmes.
        </p>

        <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
          Answers are grounded in official CHARUSAT programme documentation.
        </p>

        {/* 4 Starter Questions: 2x2 grid (1 col on mobile) */}
        <div
          className="mt-6 grid grid-cols-1 gap-2.5 sm:grid-cols-2 text-left"
          role="group"
          aria-label="Sample questions"
        >
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
