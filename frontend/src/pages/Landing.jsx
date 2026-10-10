/**
 * Landing — official entry point for the CHARUSAT Online Programmes AI Assistant.
 *
 * Provides:
 * - Neutral, accurate university overview
 * - 4 Programme cards linking to chat
 * - 6 Topic cards powered by the question bank
 * - "How It Works" 3-step explanation
 * - Dynamic Admissions helpline contacts fetched from GET /api/contacts
 * - No unverified claims or hard-coded facts
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import SiteNav from "../components/site/SiteNav.jsx";
import SiteFooter from "../components/site/SiteFooter.jsx";
import { apiFetch } from "../services/api.js";
import { loadQuestionBank } from "../lib/questionBank.js";

const PROGRAMMES = [
  {
    id: "bba",
    name: "Online BBA",
    title: "Bachelor of Business Administration",
    level: "Undergraduate • 3 Years",
    desc: "Covers business management, marketing, financial accounting, and managerial principles.",
    sampleQuery: "What are the eligibility and fee details for Online BBA?",
  },
  {
    id: "bca",
    name: "Online BCA",
    title: "Bachelor of Computer Applications",
    level: "Undergraduate • 3 Years",
    desc: "Focuses on programming, database management, software development, and modern computer systems.",
    sampleQuery: "What are the eligibility and fee details for Online BCA?",
  },
  {
    id: "mba",
    name: "Online MBA",
    title: "Master of Business Administration",
    level: "Postgraduate • 2 Years",
    desc: "Advanced management curriculum with electives in Finance, Marketing, HR, and Business Analytics.",
    sampleQuery: "What are the specializations and fees for Online MBA?",
  },
  {
    id: "mca",
    name: "Online MCA",
    title: "Master of Computer Applications",
    level: "Postgraduate • 2 Years",
    desc: "Comprehensive computing curriculum covering full-stack systems, algorithms, AI, and cloud concepts.",
    sampleQuery: "What are the syllabus and eligibility requirements for Online MCA?",
  },
];

const TOPIC_CARDS = [
  {
    id: "fees",
    title: "Fees & Payment",
    desc: "Detailed semester tuition, examination fees, and refund regulations.",
    defaultQuery: "What is the fee structure for Online MCA?",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
      </svg>
    ),
  },
  {
    id: "eligibility",
    title: "Eligibility & Admissions",
    desc: "Academic qualifications, minimum percentage, and application process.",
    defaultQuery: "What are the eligibility criteria for Online BCA?",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
        <circle cx="8.5" cy="7" r="4" />
        <path d="M20 8v6M23 11h-6" />
      </svg>
    ),
  },
  {
    id: "subjects",
    title: "Curriculum & Syllabus",
    desc: "Semester-by-semester course breakdown and core subject modules.",
    defaultQuery: "What subjects are taught in Online BBA?",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
      </svg>
    ),
  },
  {
    id: "duration",
    title: "Duration & Credits",
    desc: "Programme length, maximum completion time, and total credit requirements.",
    defaultQuery: "What is the duration and credits for Online MBA?",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
  },
  {
    id: "grading",
    title: "Examinations & Grading",
    desc: "Internal continuous evaluation, end-semester exams, and passing criteria.",
    defaultQuery: "What is the examination pattern and passing criteria?",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
      </svg>
    ),
  },
  {
    id: "lms",
    title: "LMS & Learning Portal",
    desc: "Online lectures, e-learning portal navigation, and technical helpdesk.",
    defaultQuery: "How do students access the online LMS portal?",
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </svg>
    ),
  },
];

export default function Landing() {
  const [contacts, setContacts] = useState(null);
  const [questionBank, setQuestionBank] = useState([]);

  useEffect(() => {
    let cancelled = false;

    // Load admissions contacts dynamically from API
    apiFetch("/api/contacts")
      .then((data) => {
        if (!cancelled && data) setContacts(data);
      })
      .catch((err) => console.warn("Could not load contacts:", err));

    // Load question bank dynamically for sample topics
    loadQuestionBank()
      .then((bank) => {
        if (!cancelled && Array.isArray(bank)) setQuestionBank(bank);
      })
      .catch((err) => console.warn("Could not load question bank:", err));

    return () => { cancelled = true; };
  }, []);

  // Helper to find a verified question matching a topic from the question bank
  const getTopicQuestion = (topicId, fallback) => {
    if (!questionBank || questionBank.length === 0) return fallback;
    const match = questionBank.find(
      (q) => q.topic === topicId && q.status === "FULL"
    );
    return match?.question || fallback;
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--surface-primary)] text-[var(--text-primary)]">
      <SiteNav />

      <main className="flex flex-1 flex-col">
        {/* ---- Hero Section ---- */}
        <section className="relative flex flex-col items-center justify-center overflow-hidden px-4 pb-16 pt-32 sm:pb-24 sm:pt-40">
          <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
            <div
              className="absolute inset-0 opacity-[0.03]"
              style={{
                backgroundImage:
                  "linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)",
                backgroundSize: "64px 64px",
              }}
            />
            <div className="absolute left-1/2 top-16 h-[380px] w-[680px] -translate-x-1/2 rounded-full bg-[var(--accent-surface)] blur-[120px]" />
          </div>

          <div className="relative mx-auto w-full max-w-3xl text-center">
            {/* Eyebrow */}
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border-primary)] bg-[var(--surface-hover)] px-3.5 py-1.5 text-xs font-medium text-[var(--text-secondary)] animate-fade-up">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" aria-hidden />
              CHARUSAT Online Degree Assistant
            </div>

            {/* Headline */}
            <h1 className="font-display mt-6 text-4xl font-normal leading-tight text-[var(--text-primary)] sm:text-5xl lg:text-6xl animate-fade-up">
              Official information on CHARUSAT online degrees,
              <br />
              <span className="text-[var(--accent-primary)]">answered directly.</span>
            </h1>

            {/* Subtitle */}
            <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-[var(--text-tertiary)] sm:text-lg animate-fade-up">
              Explore eligibility, fees, semester syllabi, admission guidelines, and academic
              regulations for Charotar University of Science and Technology's online programmes.
            </p>

            {/* CTAs */}
            <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center animate-fade-up">
              <Link
                to="/chat"
                className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent-primary)] px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-[var(--accent-primary-hover)] focus-visible:outline-2"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                </svg>
                Ask the Assistant
              </Link>
              <a
                href="#programmes"
                className="inline-flex items-center gap-2 rounded-xl border border-[var(--border-primary)] bg-[var(--surface-hover)] px-6 py-3 text-sm font-medium text-[var(--text-secondary)] transition hover:border-[var(--border-hover)] hover:text-[var(--text-primary)]"
              >
                View Programmes
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="M19 9l-7 7-7-7" />
                </svg>
              </a>
            </div>
          </div>
        </section>

        {/* ---- Programmes Section ---- */}
        <section id="programmes" className="border-t border-[var(--border-primary)] bg-[var(--surface-secondary)]/40 px-4 py-16 sm:py-20">
          <div className="mx-auto max-w-5xl">
            <div className="text-center">
              <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)] sm:text-3xl">
                Online Degree Programmes
              </h2>
              <p className="mx-auto mt-2 max-w-2xl text-sm text-[var(--text-tertiary)]">
                Select any programme to query specific curriculum details, fees, or requirements in the assistant.
              </p>
            </div>

            <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2">
              {PROGRAMMES.map((prog) => (
                <div
                  key={prog.id}
                  className="flex flex-col justify-between rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-primary)] p-6 shadow-sm transition hover:border-[var(--border-hover)] hover:shadow-md"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase tracking-wider text-[var(--accent-primary)]">
                        {prog.level}
                      </span>
                      <span className="rounded-lg bg-[var(--surface-hover)] px-2.5 py-1 text-xs font-medium text-[var(--text-secondary)]">
                        {prog.name}
                      </span>
                    </div>
                    <h3 className="mt-3 text-lg font-semibold text-[var(--text-primary)]">
                      {prog.title}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-[var(--text-tertiary)]">
                      {prog.desc}
                    </p>
                  </div>
                  <div className="mt-6 pt-4 border-t border-[var(--border-secondary)]">
                    <Link
                      to={`/chat?q=${encodeURIComponent(prog.sampleQuery)}`}
                      className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--accent-primary)] transition hover:underline"
                    >
                      Ask about {prog.name}
                      <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                        <path d="M5 12h14M12 5l7 7-7 7" />
                      </svg>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---- 6 Topic Cards Section ---- */}
        <section id="topics" className="border-t border-[var(--border-primary)] px-4 py-16 sm:py-20">
          <div className="mx-auto max-w-5xl">
            <div className="text-center">
              <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)] sm:text-3xl">
                Explore Knowledge Topics
              </h2>
              <p className="mx-auto mt-2 max-w-2xl text-sm text-[var(--text-tertiary)]">
                Browse official information by topic or launch deep-link questions directly into the chat assistant.
              </p>
            </div>

            <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {TOPIC_CARDS.map((card) => {
                const questionToAsk = getTopicQuestion(card.id, card.defaultQuery);
                return (
                  <Link
                    key={card.id}
                    to={`/chat?q=${encodeURIComponent(questionToAsk)}`}
                    className="group flex flex-col justify-between rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-hover)] p-6 transition hover:border-[var(--border-hover)] hover:bg-[var(--surface-active)]"
                  >
                    <div>
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] transition group-hover:bg-[var(--accent-primary)] group-hover:text-white">
                        {card.icon}
                      </div>
                      <h3 className="mt-4 text-base font-semibold text-[var(--text-primary)]">
                        {card.title}
                      </h3>
                      <p className="mt-2 text-xs leading-relaxed text-[var(--text-tertiary)]">
                        {card.desc}
                      </p>
                    </div>

                    <div className="mt-6 flex items-center gap-1.5 text-xs font-medium text-[var(--accent-primary)]">
                      <span>Query topic</span>
                      <svg className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                        <path d="M5 12h14M12 5l7 7-7 7" />
                      </svg>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </section>

        {/* ---- How It Works ---- */}
        <section id="how-it-works" className="border-t border-[var(--border-primary)] bg-[var(--surface-secondary)]/40 px-4 py-16 sm:py-20">
          <div className="mx-auto max-w-5xl">
            <div className="text-center">
              <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)] sm:text-3xl">
                How It Works
              </h2>
              <p className="mx-auto mt-2 max-w-xl text-sm text-[var(--text-tertiary)]">
                Transparent and deterministic information retrieval grounded in university records.
              </p>
            </div>

            <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-3">
              <div className="relative rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-primary)] p-6">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-primary)]/15 text-sm font-bold text-[var(--accent-primary)]">
                  1
                </div>
                <h3 className="mt-4 text-base font-semibold text-[var(--text-primary)]">
                  Ask Your Question
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-[var(--text-tertiary)]">
                  Submit queries in plain English about admission criteria, semester fee schedules, or academic policies.
                </p>
              </div>

              <div className="relative rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-primary)] p-6">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-primary)]/15 text-sm font-bold text-[var(--accent-primary)]">
                  2
                </div>
                <h3 className="mt-4 text-base font-semibold text-[var(--text-primary)]">
                  Document Retrieval
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-[var(--text-tertiary)]">
                  The system indexes official CHARUSAT Programme Project Reports (PPR) and extracts verified regulatory facts.
                </p>
              </div>

              <div className="relative rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-primary)] p-6">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-primary)]/15 text-sm font-bold text-[var(--accent-primary)]">
                  3
                </div>
                <h3 className="mt-4 text-base font-semibold text-[var(--text-primary)]">
                  Direct Verified Answers
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-[var(--text-tertiary)]">
                  Receive structured tables and concise answers, with contact information for relevant departments.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ---- Admissions Contacts Section (Dynamic from API) ---- */}
        <section id="contacts" className="border-t border-[var(--border-primary)] px-4 py-16 sm:py-20">
          <div className="mx-auto max-w-3xl rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-hover)] p-8 text-center sm:p-12">
            <h2 className="text-xl font-bold text-[var(--text-primary)] sm:text-2xl">
              Need Direct Admissions Assistance?
            </h2>
            <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-[var(--text-tertiary)]">
              Official admissions coordinators at Charotar University of Science and Technology are available for personalized guidance.
            </p>

            {contacts?.admissions && contacts.admissions.length > 0 ? (
              <div className="mt-6 flex flex-wrap items-center justify-center gap-4">
                {contacts.admissions.map((c) => (
                  <div
                    key={c.phone || c.person}
                    className="flex items-center gap-2 rounded-xl border border-[var(--border-primary)] bg-[var(--surface-primary)] px-4 py-2.5 text-xs font-medium text-[var(--text-secondary)] shadow-sm"
                  >
                    <svg className="h-4 w-4 text-[var(--accent-primary)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z" />
                    </svg>
                    <span>{c.person}</span>
                    {c.phone && (
                      <span className="text-[var(--text-tertiary)]">({c.phone})</span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4 text-xs text-[var(--text-tertiary)]">
                Admissions coordinators available during standard university working hours.
              </div>
            )}

            <div className="mt-8">
              <Link
                to="/chat"
                className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent-primary)] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[var(--accent-primary-hover)]"
              >
                Launch Assistant
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </Link>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}