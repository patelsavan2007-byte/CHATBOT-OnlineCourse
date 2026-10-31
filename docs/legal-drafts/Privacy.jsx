/**
 * Privacy Policy -- CHARUSAT Online Programmes Assistant.
 * Compliant with India's IT Act 2000, SPDI Rules 2011, and DPDP Act 2023.
 */
import { Link } from "react-router-dom";
import site from "../config/site.js";

function Section({ id, title, children }) {
  return (
    <section id={id} className="space-y-3">
      <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
        {title}
      </h2>
      <div className="space-y-2 text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
        {children}
      </div>
    </section>
  );
}

export default function Privacy() {
  const eff = site.legalEffectiveDate;
  return (
    <div className="min-h-dvh" style={{ background: "var(--page)" }}>
      <header
        className="border-b px-4 py-3.5"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <div className="mx-auto flex max-w-2xl items-center gap-3">
          <Link to="/about" className="flex h-8 w-8 items-center justify-center rounded-lg transition" style={{ color: "var(--muted)" }} aria-label="Back">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M19 12H5M12 5l-7 7 7 7" />
            </svg>
          </Link>
          <span className="text-sm font-semibold" style={{ color: "var(--text-2)" }}>Privacy Policy</span>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-2xl space-y-8 px-4 py-10 sm:px-6">
        <div>
          <h1 className="text-2xl font-semibold" style={{ color: "var(--text)" }}>Privacy Policy</h1>
          <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
            Effective: {eff} | Operator: {site.operatorName}
          </p>
        </div>

        <Section id="intro" title="1. Introduction">
          <p>
            {site.operatorName} ("we", "us", "our") operates the CHARUSAT Online
            Programmes Assistant ("Service"). This Policy explains what personal data
            we collect, why, and how we handle it.
          </p>
        </Section>

        <Section id="data-collected" title="2. Data We Collect">
          <ul className="list-disc space-y-1 pl-5">
            <li><strong>Account data:</strong> Name and email address when you register.</li>
            <li><strong>Authentication data:</strong> Hashed password or Google OAuth token. Plaintext passwords are never stored.</li>
            <li><strong>Conversation data:</strong> Questions you send and answers the assistant generates, stored to power conversation history.</li>
            <li><strong>Usage data:</strong> Query timestamps, feedback ratings (thumbs up/down) and optional correction text.</li>
            <li><strong>Technical data:</strong> Standard server logs (IP address, browser type, HTTP method) retained for up to 30 days.</li>
          </ul>
          <p>We do not collect payment card data, Aadhaar, PAN, or other government-issued identifiers.</p>
        </Section>

        <Section id="purpose" title="3. How We Use It">
          <ul className="list-disc space-y-1 pl-5">
            <li>Providing the AI Q&amp;A service and maintaining conversation history.</li>
            <li>Improving answer quality by analysing unanswered or low-rated queries.</li>
            <li>Operating the admin console to identify knowledge gaps in programme information.</li>
            <li>Complying with legal obligations.</li>
          </ul>
          <p>We do not sell, rent, or share your personal data with third parties for marketing.</p>
        </Section>

        <Section id="retention" title="4. Data Retention">
          <p>
            Conversation data is retained for {site.dataRetentionPeriod} from the date of last
            activity, after which it is automatically deleted. You may delete your account
            and all associated data at any time from Account Settings.
          </p>
        </Section>

        <Section id="your-rights" title="5. Your Rights">
          <p>Under the Digital Personal Data Protection Act 2023 (India) and applicable law, you have the right to:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>Access the personal data we hold about you.</li>
            <li>Correct inaccurate data.</li>
            <li>Erase your data (right to be forgotten).</li>
            <li>Withdraw consent, where processing is based on consent.</li>
            <li>File a complaint with the Data Protection Board of India.</li>
          </ul>
          <p>
            To exercise any of these rights, email us at{" "}
            <a href={`mailto:${site.contactEmail}`} style={{ color: "var(--accent)" }}>
              {site.contactEmail}
            </a>. We will respond within 30 days.
          </p>
        </Section>

        <Section id="cookies" title="6. Cookies and Local Storage">
          <p>
            We use browser localStorage to store your authentication token and theme
            preference. We use sessionStorage to save guest conversation history.
            We do not use third-party tracking cookies or analytics beacons.
          </p>
        </Section>

        <Section id="third-party" title="7. Third-Party Services">
          <ul className="list-disc space-y-1 pl-5">
            <li><strong>Google OAuth:</strong> If you sign in with Google, your profile data is fetched from Google APIs under their Privacy Policy.</li>
            <li><strong>Gemini API / Groq API:</strong> Questions are forwarded to these AI providers to generate answers. They do not receive your account data.</li>
          </ul>
        </Section>

        <Section id="security" title="8. Security">
          <p>
            Passwords are hashed with bcrypt. Connections are encrypted with TLS.
            Authentication tokens expire and are invalidated on logout.
            No security measure is perfect; we encourage you not to share your account credentials.
          </p>
        </Section>

        <Section id="grievance" title="9. Grievance Officer">
          <p>
            In accordance with the IT Act 2000 and DPDP Act 2023, any grievance
            relating to this Privacy Policy may be directed to:
          </p>
          <address className="not-italic">
            {site.operatorName}<br />
            Email:{" "}
            <a href={`mailto:${site.grievanceEmail}`} style={{ color: "var(--accent)" }}>
              {site.grievanceEmail}
            </a>
          </address>
        </Section>

        <Section id="changes" title="10. Changes to This Policy">
          <p>
            We may update this Policy from time to time. The effective date at the top
            of this page reflects the most recent revision. Continued use of the Service
            after changes constitutes acceptance of the updated Policy.
          </p>
        </Section>

        <div className="border-t pt-6 text-xs" style={{ borderColor: "var(--border)", color: "var(--muted)" }}>
          <Link to="/terms" style={{ color: "var(--accent)" }}>Terms of Service</Link>
          {" | "}
          <Link to="/about" style={{ color: "var(--accent)" }}>About</Link>
          {" | "}
          <Link to="/chat" style={{ color: "var(--accent)" }}>Open Assistant</Link>
        </div>
      </main>
    </div>
  );
}
