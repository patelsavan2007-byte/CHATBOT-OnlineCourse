/**
 * Landing — simple chat-first entry point.
 * The assistant is the product: this page exists to send people to /chat.
 * Sample questions deep-link with ?q= so the assistant answers immediately.
 */
import { Link } from "react-router-dom";
import SiteNav from "../components/site/SiteNav.jsx";
import SiteFooter from "../components/site/SiteFooter.jsx";

/* ---- Sample questions that pre-seed the assistant ---- */
const SAMPLE_QUESTIONS = [
  "What online programs does CHARUSAT offer?",
  "What is the fee structure for Online MBA?",
  "What are the eligibility criteria for Online BCA?",
  "How does the admission process work?",
];

const TRUST_ITEMS = [
  { val: "4", label: "Online degree programmes" },
  { val: "UGC", label: "Recognised programmes" },
  { val: "Official", label: "Answers from CHARUSAT documents" },
  { val: "24/7", label: "Always available" },
];

export default function Landing() {
  return (
    <div className="min-h-screen flex flex-col bg-[var(--surface-primary)] text-[var(--text-primary)]">
      <SiteNav />

      <main className="flex flex-1 flex-col">
        {/* ---- Hero: entry point to the assistant ---- */}
        <section className="relative flex flex-1 items-center justify-center overflow-hidden px-4 pb-20 pt-36 sm:pt-40">
          {/* Subtle geometric background */}
          <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
            <div
              className="absolute inset-0 opacity-[0.03]"
              style={{
                backgroundImage:
                  "linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)",
                backgroundSize: "64px 64px",
              }}
            />
            <div className="absolute left-1/2 top-16 h-[420px] w-[720px] -translate-x-1/2 rounded-full bg-[var(--accent-surface)] blur-[120px]" />
          </div>

          <div className="relative mx-auto w-full max-w-3xl text-center">
            {/* Eyebrow */}
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border-primary)] bg-[var(--surface-hover)] px-3.5 py-1.5 text-xs font-medium text-[var(--text-secondary)] animate-fade-up">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" aria-hidden />
              CHARUSAT AI Assistant
            </div>

            {/* Headline */}
            <h1
              className="font-display mt-6 text-4xl font-normal leading-tight text-[var(--text-primary)] sm:text-5xl lg:text-6xl animate-fade-up"
              style={{ animationDelay: "60ms" }}
            >
              Your CHARUSAT questions,
              <br />
              <em className="not-italic text-[var(--accent-primary)]">answered instantly.</em>
            </h1>

            <p
              className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-[var(--text-tertiary)] sm:text-lg animate-fade-up"
              style={{ animationDelay: "120ms" }}
            >
              Fees, eligibility, curriculum, admissions and exams for CHARUSAT's online degree
              programmes — answered directly from official documents. No searching, no guesswork.
            </p>

            {/* CTAs */}
            <div
              className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center animate-fade-up"
              style={{ animationDelay: "180ms" }}
            >
              <Link
                to="/chat"
                className="inline-flex items-center gap-2 rounded-lg bg-[var(--accent-primary)] px-6 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-[var(--accent-primary-hover)]"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                </svg>
                Ask the Assistant
              </Link>
              <Link
                to="/chat"
                className="inline-flex items-center gap-2 rounded-lg border border-[var(--border-primary)] bg-[var(--surface-hover)] px-6 py-3 text-sm font-medium text-[var(--text-secondary)] transition hover:border-[var(--border-hover)] hover:text-[var(--text-primary)]"
              >
                Try a sample question
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </Link>
            </div>

            {/* Sample questions — deep-link straight into a live chat */}
            <div
              className="mt-10 grid w-full grid-cols-1 gap-2.5 sm:grid-cols-2 animate-fade-up"
              style={{ animationDelay: "240ms" }}
            >
              {SAMPLE_QUESTIONS.map((q) => (
                <Link
                  key={q}
                  to={`/chat?q=${encodeURIComponent(q)}`}
                  className="group flex items-start gap-2.5 rounded-xl border border-[var(--border-primary)] bg-[var(--surface-hover)] p-3.5 text-left text-[13px] leading-snug text-[var(--text-secondary)] transition hover:border-[var(--border-hover)] hover:bg-[var(--surface-active)] hover:text-[var(--text-primary)]"
                >
                  <svg className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--accent-primary)] opacity-70 transition group-hover:opacity-100" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                  </svg>
                  {q}
                </Link>
              ))}
            </div>

            {/* Trust indicators */}
            <div
              className="mx-auto mt-12 grid max-w-lg grid-cols-2 divide-x divide-[var(--border-secondary)] overflow-hidden rounded-xl border border-[var(--border-primary)] bg-[var(--surface-hover)] text-center animate-fade-up sm:grid-cols-4"
              style={{ animationDelay: "300ms" }}
            >
              {TRUST_ITEMS.map(({ val, label }) => (
                <div key={label} className="px-2 py-4">
                  <div className="text-sm font-semibold text-[var(--text-primary)]">{val}</div>
                  <div className="mt-1 text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}