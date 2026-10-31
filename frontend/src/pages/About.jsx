/**
 * About page - concise, calm, and grounded overview of the CCOE CHARUSAT Assistant.
 * Strictly under 250 words, single column centered at 640px, with verified contacts only.
 */
import { Link, useNavigate } from "react-router-dom";
import LogoLockup from "../components/ui/LogoLockup.jsx";

export default function About() {
  const navigate = useNavigate();

  const handleBack = () => {
    if (window.history.state?.idx > 0) {
      navigate(-1);
    } else {
      navigate("/");
    }
  };

  return (
    <div
      className="min-h-dvh flex flex-col font-sans"
      style={{ background: "var(--page)", color: "var(--text)" }}
    >
      {/* Top Navigation */}
      <header
        className="sticky top-0 z-30 border-b px-4 py-3"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <div className="mx-auto flex max-w-[640px] items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={handleBack}
              className="flex h-8 w-8 items-center justify-center rounded-md border text-xs font-medium transition hover:border-[var(--border-focus)] cursor-pointer"
              style={{
                borderColor: "var(--border)",
                background: "var(--surface-2)",
                color: "var(--text)",
                borderRadius: "6px",
              }}
              aria-label="Back to chat"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M19 12H5M12 5l-7 7 7 7" />
              </svg>
            </button>
            <span className="text-sm font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              About this assistant
            </span>
          </div>
          <Link
            to="/chat"
            className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--border-focus)]"
            style={{
              borderColor: "var(--border)",
              background: "var(--surface)",
              color: "var(--text)",
              borderRadius: "6px",
            }}
          >
            Chat
          </Link>
        </div>
      </header>

      {/* Main Single Column (max-w 640px) */}
      <main className="mx-auto max-w-[640px] flex-1 px-4 py-8 sm:px-6 w-full space-y-6">
        {/* Header / Logo Lockup */}
        <div className="space-y-4">
          <div className="flex justify-start">
            <LogoLockup height={36} />
          </div>
          <h1 className="text-xl sm:text-2xl font-semibold tracking-tight" style={{ color: "var(--text)" }}>
            About this assistant
          </h1>
        </div>

        {/* Section 1: What this assistant is */}
        <section
          className="rounded-lg border p-5 space-y-2"
          style={{ background: "var(--surface)", borderColor: "var(--border)", borderRadius: "8px" }}
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
            What this assistant is
          </h2>
          <p className="text-xs sm:text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
            This is the official AI assistant for prospective and enrolled learners of the Center for Online Education (CCOE) at Charotar University of Science and Technology (CHARUSAT).
          </p>
        </section>

        {/* Section 2: What it can answer */}
        <section
          className="rounded-lg border p-5 space-y-2"
          style={{ background: "var(--surface)", borderColor: "var(--border)", borderRadius: "8px" }}
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
            What it can answer
          </h2>
          <p className="text-xs sm:text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
            It answers questions regarding fee structures, eligibility criteria, semester-wise subjects, admissions, examinations, and LMS access for online BBA, BCA, MBA and MCA programmes.
          </p>
        </section>

        {/* Section 3: Document sources and disclaimer */}
        <section
          className="rounded-lg border p-5 space-y-2"
          style={{ background: "var(--surface)", borderColor: "var(--border)", borderRadius: "8px" }}
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
            Document sources and disclaimer
          </h2>
          <p className="text-xs sm:text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
            Answers are grounded in official CCOE programme documentation. If a policy or fee changes, the official university notification takes precedence. It does not replace academic advising or make admission decisions.
          </p>
        </section>

        {/* Section 4: Official contact */}
        <section
          className="rounded-lg border p-5 space-y-3"
          style={{ background: "var(--surface)", borderColor: "var(--border)", borderRadius: "8px" }}
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
            Official contact
          </h2>
          <div className="space-y-2 text-xs sm:text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
            <p>
              <strong style={{ color: "var(--text)" }}>Admission Helpline:</strong>{" "}
              +91 7434055553, +91 7600257365 (online-admissions@charusat.ac.in)
            </p>
            <p>
              <strong style={{ color: "var(--text)" }}>Student Support:</strong>{" "}
              +91 9408033391 (student.services@charusat.ac.in)
            </p>
            <p>
              <strong style={{ color: "var(--text)" }}>Official Website:</strong>{" "}
              <a
                href="https://charusat.online"
                target="_blank"
                rel="noopener noreferrer"
                className="underline transition hover:opacity-80"
                style={{ color: "var(--accent)" }}
              >
                charusat.online
              </a>
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer
        className="border-t px-4 py-6 text-center text-xs"
        style={{ borderColor: "var(--border)", color: "var(--muted)", background: "var(--surface)" }}
      >
        <div className="mx-auto max-w-[640px] flex flex-col items-center gap-2">
          <Link to="/chat" className="hover:underline" style={{ color: "var(--text-2)" }}>
            Return to chat
          </Link>
          <p className="font-mono text-[11px]">
            {new Date().getFullYear()} Center for Online Education (CCOE), CHARUSAT. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
