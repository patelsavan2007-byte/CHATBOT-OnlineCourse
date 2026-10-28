/**
 * About -- what the CHARUSAT Online Programmes Assistant is, its scope,
 * data sources, and who operates it.
 */
import { Link } from "react-router-dom";
import site from "../config/site.js";

function PageShell({ title, children }) {
  return (
    <div className="min-h-dvh" style={{ background: "var(--page)", color: "var(--text)" }}>
      <header
        className="border-b px-4 py-3.5"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <div className="mx-auto flex max-w-2xl items-center gap-3">
          <Link
            to="/chat"
            className="flex h-8 w-8 items-center justify-center rounded-lg transition"
            style={{ color: "var(--muted)" }}
            aria-label="Back to assistant"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M19 12H5M12 5l-7 7 7 7" />
            </svg>
          </Link>
          <span className="text-sm font-semibold" style={{ color: "var(--text-2)" }}>
            {title}
          </span>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
        {children}
      </main>

      <footer
        className="border-t px-4 py-6 text-center text-xs"
        style={{ borderColor: "var(--border)", color: "var(--muted)" }}
      >
        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
          <Link to="/about" style={{ color: "var(--muted)" }}>About</Link>
          <Link to="/privacy" style={{ color: "var(--muted)" }}>Privacy</Link>
          <Link to="/terms" style={{ color: "var(--muted)" }}>Terms</Link>
          <Link to="/chat" style={{ color: "var(--muted)" }}>Open Assistant</Link>
        </div>
        <p className="mt-2">{new Date().getFullYear()} {site.operatorName}. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default function About() {
  return (
    <PageShell title="About">
      <article className="prose-chat space-y-6">
        <h1 className="text-2xl font-semibold" style={{ color: "var(--text)" }}>
          About the CHARUSAT Online Programmes Assistant
        </h1>

        <section>
          <h2>What it is</h2>
          <p>
            This is an AI-powered question-answering assistant that answers student
            queries about CHARUSAT's officially approved online degree programmes:
            BBA, BCA, MBA, and MCA. It is operated by {site.operatorName}.
          </p>
        </section>

        <section>
          <h2>What it can answer</h2>
          <ul>
            <li>Programme eligibility and entry requirements</li>
            <li>Fee structures, payment schedules, and scholarships</li>
            <li>Curriculum, subjects, and semester breakdown</li>
            <li>Admission process, dates, and required documents</li>
            <li>Examination patterns and rules</li>
            <li>LMS access, student support, and contact details</li>
          </ul>
        </section>

        <section>
          <h2>Data sources</h2>
          <p>
            Answers are generated from CHARUSAT's official programme brochures,
            fee circulars, UGC approval letters, and admissions notices. All source
            documents are curated and maintained by the university.
          </p>
        </section>

        <section>
          <h2>Limitations</h2>
          <p>
            The assistant may occasionally be incorrect or out of date, particularly
            for information that changes frequently (such as fee revisions or exam
            schedules). Always verify time-sensitive details with the admissions office.
          </p>
          <p>
            The assistant does not answer questions outside the scope of CHARUSAT's
            online programmes, provide legal or financial advice, or access your
            personal university account.
          </p>
        </section>

        <section>
          <h2>Contact</h2>
          <p>
            For admissions enquiries, contact the online programmes office directly
            via the phone numbers and email addresses listed on{" "}
            <a
              href={site.universityUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              {site.universityUrl}
            </a>.
          </p>
        </section>
      </article>
    </PageShell>
  );
}
