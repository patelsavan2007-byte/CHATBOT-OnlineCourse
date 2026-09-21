/**
 * SiteFooter — concise footer for the landing page.
 * Points to the assistant plus the key programmes it covers.
 */
import { Link } from "react-router-dom";

const PROGRAM_LABELS = ["Online BBA", "Online BCA", "Online MBA", "Online MCA"];

const ACCREDITATIONS = [
  "NAAC Graded A+",
  "NIRF Top 200",
  "UGC Recognised",
  "Govt. of Gujarat CoE",
];

export default function SiteFooter() {
  return (
    <footer className="border-t border-[var(--border-primary)] bg-[var(--surface-secondary)]">
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
        {/* Top row */}
        <div className="flex flex-col items-start justify-between gap-8 sm:flex-row sm:items-center">
          {/* Brand */}
          <div className="max-w-sm">
            <Link to="/" className="inline-flex items-center gap-2.5" aria-label="CHARUSAT AI Assistant home">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-primary)]/90">
                <svg viewBox="0 0 24 24" className="h-4.5 w-4.5 fill-white" aria-hidden>
                  <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
                </svg>
              </span>
              <span className="text-sm font-semibold text-[var(--text-primary)]">CHARUSAT Assistant</span>
            </Link>
            <p className="mt-3 text-sm leading-relaxed text-[var(--text-tertiary)]">
              An AI assistant for CHARUSAT's online degree programmes. Answers are drawn from the
              university's official documents — fees, eligibility, curriculum, admissions and exams.
            </p>
          </div>

          {/* Programmes covered */}
          <div>
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-[var(--text-muted)]">
              Ask about
            </h3>
            <ul className="grid grid-cols-2 gap-x-8 gap-y-2">
              {PROGRAM_LABELS.map((label) => (
                <li key={label}>
                  <Link to="/chat" className="text-sm text-[var(--text-tertiary)] transition hover:text-[var(--text-primary)]">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Accreditations */}
          <div className="max-w-[220px]">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-[var(--text-muted)]">
              Institution
            </h3>
            <div className="flex flex-wrap gap-2">
              {ACCREDITATIONS.map((a) => (
                <span
                  key={a}
                  className="inline-block rounded-md border border-[var(--border-primary)] bg-[var(--surface-hover)] px-2.5 py-1 text-[11px] font-medium text-[var(--text-secondary)]"
                >
                  {a}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 flex flex-col gap-2 border-t border-[var(--border-primary)] pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-[var(--text-muted)]">
            © {new Date().getFullYear()} Charotar University of Science and Technology. All rights reserved.
          </p>
          <p className="text-xs text-[var(--text-muted)]">
            Confirm binding admission decisions with CHARUSAT's Admissions Office.
          </p>
        </div>
      </div>
    </footer>
  );
}