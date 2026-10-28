/**
 * About - what the CHARUSAT Online Programmes Assistant is, its scope,
 * data sources, limitations, official contacts, and operator details.
 */
import { Link } from "react-router-dom";
import site from "../config/site.js";

function PageShell({ title, children }) {
  return (
    <div className="min-h-dvh flex flex-col font-sans" style={{ background: "var(--page)", color: "var(--text)" }}>
      <header
        className="sticky top-0 z-30 border-b px-4 py-3"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <div className="mx-auto flex max-w-2xl items-center gap-3">
          <Link
            to="/chat"
            className="flex h-8 w-8 items-center justify-center rounded-md border text-xs font-medium transition hover:border-[var(--border-focus)]"
            style={{
              borderColor: "var(--border)",
              background: "var(--surface-2)",
              color: "var(--text)",
            }}
            aria-label="Back to chat"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M19 12H5M12 5l-7 7 7 7" />
            </svg>
          </Link>
          <span className="text-sm font-semibold tracking-tight" style={{ color: "var(--text)" }}>
            {title}
          </span>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-2xl flex-1 px-4 py-8 sm:px-6 w-full">
        {children}
      </main>

      <footer
        className="border-t px-4 py-6 text-center text-xs"
        style={{ borderColor: "var(--border)", color: "var(--muted)", background: "var(--surface)" }}
      >
        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
          <Link to="/about" style={{ color: "var(--text-2)" }}>About</Link>
          <Link to="/privacy" style={{ color: "var(--text-2)" }}>Privacy Policy</Link>
          <Link to="/terms" style={{ color: "var(--text-2)" }}>Terms of Service</Link>
          <Link to="/chat" style={{ color: "var(--text-2)" }}>Return to chat</Link>
        </div>
        <p className="mt-2 font-mono text-[11px]">
          {new Date().getFullYear()} {site.operatorName}. All rights reserved.
        </p>
        {!site.operatedByCharusat && (
          <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
            Independent project, not operated by CHARUSAT.
          </p>
        )}
      </footer>
    </div>
  );
}

export default function About() {
  return (
    <PageShell title="About Assistant">
      <article className="space-y-6 text-xs sm:text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight" style={{ color: "var(--text)" }}>
            About the CHARUSAT Online Programmes Assistant
          </h1>
          <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
            Operational reference and directory for students and applicants
          </p>
        </div>

        {!site.operatedByCharusat && (
          <div
            className="rounded-md border p-3 text-xs"
            style={{
              borderColor: "var(--border)",
              background: "var(--surface-2)",
              color: "var(--text-2)",
            }}
          >
            Independent project, not operated by CHARUSAT.
          </div>
        )}

        <section
          className="rounded-lg border p-5 space-y-2"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
            Purpose and Scope
          </h2>
          <p>
            This is a question-answering assistant for CHARUSAT's officially approved online degree programmes:
            Bachelor of Business Administration (BBA), Bachelor of Computer Applications (BCA), Master of Business
            Administration (MBA), and Master of Computer Applications (MCA).
          </p>
          <p>
            It is operated by {site.operatorName} to help prospective and enrolled students quickly find specific
            information from official academic documents.
          </p>
        </section>

        <section
          className="rounded-lg border p-5 space-y-2"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
            What You Can Ask
          </h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Programme eligibility criteria, minimum percentages, and prerequisite degrees</li>
            <li>Semester-wise fee schedules, payment methods, and installment plans</li>
            <li>Curriculum outlines, core and elective course lists, and credit structures</li>
            <li>Admission dates, document checklists, and application guidelines</li>
            <li>Examination structures, continuous internal evaluations, and term-end patterns</li>
            <li>Learning Management System (LMS) navigation and designated university support desks</li>
          </ul>
        </section>

        <section
          className="rounded-lg border p-5 space-y-2"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
            Knowledge Base and Grounding
          </h2>
          <p>
            Every answer is retrieved directly from official university documents, including programme handbooks,
            approved syllabi, fee circulars, and notifications.
          </p>
          <p>
            When an answer is provided, the exact source document name and relevant page number are attached.
            If information is not contained in approved documents, the assistant acknowledges the gap rather than
            fabricating details.
          </p>
        </section>

        <section
          className="rounded-lg border p-5 space-y-2"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
            Important Disclaimer
          </h2>
          <p>
            Answers generated by this assistant are informational only. Binding admission decisions, fee structures,
            scholarships, and formal enrollment obligations must be confirmed directly with the official Admissions Office.
          </p>
          <p>
            The assistant does not have access to personal student records, fee payment receipts, or confidential
            examination results.
          </p>
        </section>

        <section
          className="rounded-lg border p-5 space-y-3"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
            Official University Contact Directory
          </h2>
          <p className="text-xs" style={{ color: "var(--muted)" }}>
            Contacts published in official CHARUSAT online programme documentation:
          </p>

          <div className="overflow-x-auto rounded border" style={{ borderColor: "var(--border)" }}>
            <table className="w-full text-left text-xs border-collapse">
              <thead
                className="border-b text-[10px] uppercase font-semibold tracking-wider"
                style={{ background: "var(--surface-2)", borderColor: "var(--border)", color: "var(--muted)" }}
              >
                <tr>
                  <th className="px-3 py-2">Department</th>
                  <th className="px-3 py-2">Contact Person</th>
                  <th className="px-3 py-2">Email</th>
                  <th className="px-3 py-2">Helpline</th>
                </tr>
              </thead>
              <tbody className="divide-y font-mono text-[11px]" style={{ borderColor: "var(--border)" }}>
                <tr>
                  <td className="px-3 py-2 font-sans font-medium text-[var(--text)]">Admissions &amp; Fees</td>
                  <td className="px-3 py-2 font-sans">Mr. Darshit Patel / Mr. Kirti Patel</td>
                  <td className="px-3 py-2">online-admissions@charusat.ac.in</td>
                  <td className="px-3 py-2 whitespace-nowrap">7434055553 / 7600257365</td>
                </tr>
                <tr>
                  <td className="px-3 py-2 font-sans font-medium text-[var(--text)]">Student Services</td>
                  <td className="px-3 py-2 font-sans">Mr. Mitesh Patel</td>
                  <td className="px-3 py-2">student.services@charusat.ac.in</td>
                  <td className="px-3 py-2 whitespace-nowrap">9408033391</td>
                </tr>
                <tr>
                  <td className="px-3 py-2 font-sans font-medium text-[var(--text)]">LMS (BCA / MCA)</td>
                  <td className="px-3 py-2 font-sans">Mr. Sanket Patel / Mr. Ravi Patel</td>
                  <td className="px-3 py-2">lms@charusat.ac.in</td>
                  <td className="px-3 py-2 whitespace-nowrap">8460549025 / 7574945238</td>
                </tr>
                <tr>
                  <td className="px-3 py-2 font-sans font-medium text-[var(--text)]">LMS (BBA / MBA)</td>
                  <td className="px-3 py-2 font-sans">Ms. Subhashree S</td>
                  <td className="px-3 py-2">lms@charusat.ac.in</td>
                  <td className="px-3 py-2 whitespace-nowrap">9688397401</td>
                </tr>
                <tr>
                  <td className="px-3 py-2 font-sans font-medium text-[var(--text)]">Course Mentor</td>
                  <td className="px-3 py-2 font-sans">Dr. Hetal Barad</td>
                  <td className="px-3 py-2">course.mentor@charusat.ac.in</td>
                  <td className="px-3 py-2 whitespace-nowrap">7434055556</td>
                </tr>
                <tr>
                  <td className="px-3 py-2 font-sans font-medium text-[var(--text)]">Examinations</td>
                  <td className="px-3 py-2 font-sans">Mr. Snehal Patel</td>
                  <td className="px-3 py-2">exam@charusat.ac.in</td>
                  <td className="px-3 py-2 whitespace-nowrap">9409572216</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="text-xs">
            For general university enquiries, visit the official university portal at{" "}
            <a
              href={site.universityUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
              style={{ color: "var(--accent)" }}
            >
              {site.universityUrl}
            </a>.
          </p>
        </section>
      </article>
    </PageShell>
  );
}
