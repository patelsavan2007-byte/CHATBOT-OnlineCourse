/**
 * Terms of Service -- CHARUSAT Online Programmes Assistant.
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

export default function Terms() {
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
          <span className="text-sm font-semibold" style={{ color: "var(--text-2)" }}>Terms of Service</span>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-2xl space-y-8 px-4 py-10 sm:px-6">
        <div>
          <h1 className="text-2xl font-semibold" style={{ color: "var(--text)" }}>Terms of Service</h1>
          <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
            Effective: {eff} | Operator: {site.operatorName}
          </p>
        </div>

        <Section id="acceptance" title="1. Acceptance">
          <p>
            By using the CHARUSAT Online Programmes Assistant ("Service"), you agree
            to these Terms. If you do not agree, do not use the Service.
          </p>
        </Section>

        <Section id="service" title="2. The Service">
          <p>
            The Service provides AI-generated answers to questions about CHARUSAT's
            online degree programmes (BBA, BCA, MBA, MCA), based on official programme
            documents maintained by {site.operatorName}.
          </p>
          <p>
            Answers are informational only. They do not constitute official admission
            offers, fee commitments, or academic guarantees. Always verify
            time-sensitive details with the admissions office.
          </p>
        </Section>

        <Section id="account" title="3. Your Account">
          <p>
            You are responsible for maintaining the confidentiality of your login
            credentials and for all activity under your account. Notify us immediately
            if you suspect unauthorised access.
          </p>
          <p>
            Guest mode allows limited use without registration. Guest conversations
            are stored only in your browser and are not recoverable if you clear your
            browser data.
          </p>
        </Section>

        <Section id="acceptable-use" title="4. Acceptable Use">
          <p>You agree not to:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>Attempt to extract, reverse-engineer, or reproduce the underlying knowledge base.</li>
            <li>Submit content that is defamatory, abusive, unlawful, or designed to harm others.</li>
            <li>Use automated tools to send queries at a rate that degrades the Service for others.</li>
            <li>Attempt to circumvent authentication or security controls.</li>
          </ul>
        </Section>

        <Section id="accuracy" title="5. Accuracy Disclaimer">
          <p>
            The Service uses a large language model (LLM) to generate answers from
            curated source documents. AI responses may contain errors or omissions.
            {site.operatorName} does not warrant the accuracy, completeness, or
            timeliness of any answer. Use answers as a starting point and confirm
            important decisions with official university sources.
          </p>
        </Section>

        <Section id="ip" title="6. Intellectual Property">
          <p>
            The Service, its design, and its underlying knowledge base are the property
            of {site.operatorName}. You may use the Service for personal, non-commercial
            enquiry purposes only. Systematic reproduction of the knowledge base is
            prohibited.
          </p>
        </Section>

        <Section id="privacy" title="7. Privacy">
          <p>
            Use of the Service is also governed by our{" "}
            <Link to="/privacy" style={{ color: "var(--accent)" }}>Privacy Policy</Link>.
          </p>
        </Section>

        <Section id="termination" title="8. Termination">
          <p>
            We may suspend or terminate access to the Service for violations of
            these Terms, without notice and at our sole discretion. You may
            terminate your account at any time from Account Settings.
          </p>
        </Section>

        <Section id="liability" title="9. Limitation of Liability">
          <p>
            To the maximum extent permitted by applicable law, {site.operatorName}
            shall not be liable for any indirect, incidental, or consequential
            damages arising from use of or inability to use the Service.
          </p>
        </Section>

        <Section id="governing-law" title="10. Governing Law">
          <p>
            These Terms are governed by the laws of {site.jurisdiction}. Disputes
            shall be subject to the exclusive jurisdiction of courts in{" "}
            {site.jurisdiction}.
          </p>
        </Section>

        <Section id="changes" title="11. Changes">
          <p>
            We may revise these Terms at any time. The effective date at the top
            reflects the most recent revision. Continued use after changes
            constitutes acceptance.
          </p>
        </Section>

        <Section id="contact" title="12. Contact">
          <p>
            Questions about these Terms:{" "}
            <a href={`mailto:${site.contactEmail}`} style={{ color: "var(--accent)" }}>
              {site.contactEmail}
            </a>
          </p>
        </Section>

        <div className="border-t pt-6 text-xs" style={{ borderColor: "var(--border)", color: "var(--muted)" }}>
          <Link to="/privacy" style={{ color: "var(--accent)" }}>Privacy Policy</Link>
          {" | "}
          <Link to="/about" style={{ color: "var(--accent)" }}>About</Link>
          {" | "}
          <Link to="/chat" style={{ color: "var(--accent)" }}>Open Assistant</Link>
        </div>
      </main>
    </div>
  );
}
