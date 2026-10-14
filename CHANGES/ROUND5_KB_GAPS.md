# ROUND 5 — Knowledge Base Gaps Report

**Date:** 2026-10-14  
**Note:** No KB files were changed. This is a report only.

---

## Table 1: Topics Not in Any Document

| Topic / Question | Where to get it |
|-----------------|-----------------|
| BBA/MBA mandatory admission documents list | Not in online_bba.md or online_mba.md FAQ (only BCA/MCA FAQ has it) |
| Scholarship or fee discount details | Not in any KB file |
| Mobile app for LMS (yes/no) | Not mentioned |
| Internship / project details per programme | Not in KB (only generic mention in home.md) |
| Tax invoice or GST on fees | Not in KB |
| Student ID card issuance process | Not in KB |
| Faculty list / names per programme | Not in KB (only Dr. Hetal Barad as Course Mentor in contact.md) |
| Entrance exam / test details | Not in KB (only eligibility: 12th pass, no entrance test mentioned) |
| EMI payment options | Not in any KB file |
| Assignment submission deadlines | Not in any KB file |
| Certificate issuance timeline | Not in any KB file |
| International student / NRI admission | Not specifically addressed |
| Technical requirements for LMS access | Not in KB |

---

## Table 2: In the Documents But Not Reliably Retrieved

| Topic | File | Location | Retrieval Risk |
|-------|------|----------|---------------|
| BBA exam fee (Rs.1,500/semester) | PPR_Online BBA.pdf | Fee table, pages 6-8 | PDF fee-table chunk may not be top-6; Step 4 fee_candidate_search should help |
| BCA/MCA mandatory document list | programs/online_bca.md | FAQ section, line ~200 | Long file; FAQ chunk may score low for "documents required" follow-up |
| WES evaluation | programs/online_bca.md | FAQ section | Same risk as above |
| Live webinar attendance tracking | terms-conditions.md | Section on attendance | Generic topic; may not be retrieved for attendance questions |
| Refund policy details | knowledge_base/pdfs/Fees Refund Policy.pdf | Full document | Only retrieved if topic=refund; now reachable with fixed refund regex |
| Grading 36% pass rule | All 4 PPR PDFs | Grading section | Present in retrieved pool, but long PDFs need correct chunk to surface |
| BCA 50/50 vs 30/70 conflict | PPR_Online BCA.pdf | Text vs. course tables | Both chunks rarely retrieved together |

---

## Table 3: Contradictions Between Documents

| Attribute | Document A | Value A | Document B | Value B | Nature |
|-----------|-----------|---------|-----------|---------|--------|
| BCA internal marks | PPR_Online BCA.pdf, text section | 50 internal / 50 external | PPR_Online BCA.pdf, course tables | 30 internal / 70 external | Real intra-document conflict |
| MBA evaluation | PPR_Online MBA.pdf | 50/50 | (None) | — | No conflict; MBA is consistent |
| BBA evaluation | PPR_Online BBA.pdf | 30/70 | programs/online_bba.md | Not stated | No conflict; MD does not state it |

---

## Notes on Stray File and Ingestion

### `backend/knowledge_base/pdfs/Untitled-1.txt`

- This file is a saved Google Sheets page (fee data table).
- It contains structured fee data for all 4 programmes.
- **Ingestion:** `PDFIngester.get_pdf_files()` filters `suffix.lower() == ".pdf"` so this `.txt` file is **not ingested**. It is inert.
- **Recommendation:** Either delete it (it is not committed to git, only in working tree) or ingest it as a structured data source if the fee table data in it is more complete than what the PDFs provide.

### Scraper / FAQ Issues (Step 8c — report only)

1. **FAQ question text lost:** The MCA and BCA FAQ pages have answer paragraphs but the question headings were not captured by the scraper. Chunks contain the answer text but not the question, so a user asking in a question-style gets a worse semantic match.

2. **"Our Recruiters" section empty:** `home.md` has an "Our Recruiters" heading with no company names — the scraper captured the heading but the company logo images had no alt text.

3. **Obfuscated emails in contact.md:** All email addresses appear as `[email protected]` (Cloudflare email protection). The scraper cannot decode these. This is expected behaviour; the system currently does not expose email addresses to users, so this is acceptable.
