/**
 * site.js - Operator configuration for the CHARUSAT Online Programmes Assistant.
 *
 * Values marked CONFIRM must be filled in before production launch.
 * The build script (check-rules.mjs) will fail if any value is still "CONFIRM".
 *
 * Because operatedByCharusat is true, the site may use CHARUSAT copyright
 * and claim official status on /about.
 */

const site = {
  /** Short name shown in the header wordmark and page titles. */
  shortName: "CHARUSAT Assistant",

  /** Full product name used in meta descriptions. */
  fullName: "CHARUSAT Online Programmes Assistant",

  /** The organization operating this site. */
  operatorName: "Charotar University of Science and Technology",

  /**
   * Set to true only if this site is officially operated by CHARUSAT.
   * Controls whether /about says "official" and whether CHARUSAT copyright appears.
   */
  operatedByCharusat: true,

  /** Public domain where this site is deployed. Fill in after DNS is connected. */
  domain: "CONFIRM",

  /** Primary contact email. */
  contactEmail: "CONFIRM",

  /**
   * Grievance officer email for India DPDP Act 2023 compliance.
   * May be the same as contactEmail if no separate officer is designated.
   */
  grievanceEmail: "CONFIRM",

  /** Governing jurisdiction for internal configuration. */
  jurisdiction: "Gujarat, India",

  /**
   * How long conversation data is retained before automatic deletion.
   * Retention policy setting. Example: "12 months".
   */
  dataRetentionPeriod: "CONFIRM",

  /**
   * Effective date for internal policy records.
   * Format: YYYY-MM-DD. Update whenever either document changes.
   */
  legalEffectiveDate: "2026-10-28",

  /** Official CHARUSAT website for external links. */
  universityUrl: "https://charusat.ac.in",

  /** Official support / helpline contact for the online programmes office. */
  supportPhone: "CONFIRM",
};

// Build-time guard: the check-rules script will also catch CONFIRM values,
// but we add a runtime guard here so a missed placeholder is obvious in dev.
if (typeof window !== "undefined" && import.meta.env.DEV) {
  const missing = Object.entries(site)
    .filter(([, v]) => v === "CONFIRM")
    .map(([k]) => k);
  if (missing.length) {
    console.warn(
      "[site.js] The following config values need to be filled in:",
      missing
    );
  }
}

export default site;
