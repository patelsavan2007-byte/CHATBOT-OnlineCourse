# Round 5B Knowledge Base Gap & Contradiction Report

**Generated:** 2026-10-14  
**Audit Scope:** CHARUSAT Online Course Chatbot Knowledge Base (`backend/knowledge_base/`)  
**Methodology:** Fact-level cross-verification against raw PDF Programme Project Reports (PPR) and scraped markdown files (`online_bba.md`, `online_bca.md`, `online_mba.md`, `online_mca.md`, `terms-conditions.md`, `contact.md`).

---

## 1. Contradictions in Official Documents

These are discrepancies and inconsistencies directly present across the official university documents.

| ID | Topic / Attribute | Programmes Affected | Source 1 & Value | Source 2 & Value | Root Cause & Resolution |
|---|---|---|---|---|---|
| C-01 | Internal / External Examination Split | Online BCA | `PPR_Online BCA.pdf`, Page 10, Section 5: **50% Internal (Continuous Evaluation) / 50% Final University Examination** | `PPR_Online BCA.pdf`, Page 6, Course Structure Scheme: **30% Internal / 70% University Examination** | Document draft mismatch between summary narrative (50/50) and semester course scheme table (30/70). RAG conflict detector surfaces both figures. |
| C-02 | Total Programme Credits | Online BBA | `PPR_Online BBA.pdf`, Page 4 & Page 6: **130 Credits** (6 semesters) | `PPR_Online BBA.pdf`, Page 9, Evaluation Scheme: **120 Credits** | Total credits updated in course matrix (130) but legacy summary table (120) retained in document. Conflict detector surfaces both figures. |
| C-03 | Total Programme Credits | Online MBA | `PPR_Online MBA.pdf`, Page 4 & Page 10: **102 Credits** (4 semesters) | `PPR_Online MBA.pdf`, Page 12: **100 Credits** | Minor credit audit discrepancy between specialization electives table and core credit summary. |
| C-04 | MCA Eligibility Criteria in Web FAQ | Online MCA | `PPR_Online MCA.pdf`, Page 3: **Passed BCA / Bachelor Degree in Computer Science Engineering or equivalent, OR Passed B.Sc./B.Com/B.A. with Mathematics at 10+2 level or graduation level** | `online_mca.md`, Line 14 (FAQ): *"Passed 10+2 examination in any stream"* | Typographical / template copy-paste error from BCA/BBA web page onto the MCA FAQ section. Chatbot correctly routes to PPR official criteria. |
| C-05 | BBA Grading Table Discontinuity | Online BBA | `PPR_Online BBA.pdf`, Page 10, Table: **Grade O: ≥96%**, **Grade A+: <95% to 85%** | `PPR_Online BBA.pdf`, Page 10: **Pass: ≥36%**, **Fail: <35%** | Gaps in official grading range: 95.0%–95.9% is unassigned between Grade O and Grade A+; 35.0%–35.9% is unassigned between Pass and Fail. |

---

## 2. In Documents but Historically Under-Retrieved (Resolved in Round 5B)

These facts exist in official university documents but previously failed to retrieve due to strict programme filtering or stem mismatches before Round 5B lexicon fixes.

| ID | Information Item | Exact Source File & Location | Verified Factual Content | Retrieval Fix Applied |
|---|---|---|---|---|
| R-01 | BBA Internship Project Name | `PPR_Online BBA.pdf`, Page 8, Line 76 | **"Organizational Attachment Programme"** (Semester VI, Course Code BB606, 6 Credits) | Multi-label lexicon mapping for `internship_projects` with synonym expansions. |
| R-02 | MBA Industrial Training Project | `PPR_Online MBA.pdf`, Page 7, Line 71 | **"Comprehensive Project - Industrial Training"** (Semester IV, Course Code MB405, 6 Credits) | Multi-label lexicon mapping for `internship_projects`. |
| R-03 | MCA Dissertation Project Work | `PPR_Online MCA.pdf`, Page 6, Line 73 | **"Dissertation / Project Work - Industrial Training"** (Semester IV, Course Code MC406, 12 Credits) | Multi-label lexicon mapping for `internship_projects`. |
| R-04 | WES Credential Recognition | `online_bca.md`, Line 285 & `online_mca.md`, Line 259 | Explicitly confirmed: *"Is Online BCA/MCA degree recognized by WES? Yes, CHARUSAT degrees are recognized by World Education Services (WES) for higher education and immigration abroad."* | Programme-independent topic retrieval for WES and international equivalence. |
| R-05 | Mandatory Webinar Attendance | `terms-conditions.md`, Line 24 | Explicitly stated: Mandatory attendance tracked through the LMS platform for live webinars and online interactive sessions. | Programme-independent topic classification in `topic_lexicon.json`. |
| R-06 | BBA Examination Fee & Total Fee | `PPR_Online BBA.pdf`, Page 10 | Examination Fee: **Rs. 1,500 per semester** (Rs. 9,000 total across 6 semesters). Total Course Fee: **Rs. 1,59,000** (Tuition Rs. 1,50,000 + Exam Fee Rs. 9,000). | Step 4c fee table candidate search guarantee in `retriever.py`. |
| R-07 | EMI and Payment Installment Availability | `terms-conditions.md`, Line 42 | No-cost EMI and flexible installment payment options available through authorized banking partners. | Added `emi` topic with `Accounts & Payments` contact routing. |

---

## 3. Not in Documents (True Knowledge Base Gaps)

These queries cannot be answered from the current knowledge base because the underlying documents do not contain the specific facts. The chatbot properly returns an honest safe refusal and routes to the designated university department.

| ID | Query Topic | Missing Detail | Designated Contact Service | Official Contact Department |
|---|---|---|---|---|
| G-01 | Individual Faculty Names & Profiles | Complete faculty roster with individual professor names, designations, and research backgrounds for specific courses. (Documents only state general UGC faculty qualifications). | `Course Mentor` / `Admissions` | Dr. Hetal Barad (7434055556) |
| G-02 | Cohort Specific Application Deadlines | Exact calendar cutoff dates for 2026-2027 admissions cycle cohorts (only semester lengths and general eligibility are documented). | `Admissions` | Mr. Darshit Patel (7434055553), Mr. Kirti Patel (7600257365) |
| G-03 | Specific Company Drive Schedules | Specific list of companies visiting for next year's campus recruitment drives (general placement assistance policy is documented, but dynamic company recruitment schedules are not published in PPRs). | `Student Services` | Mr. Mitesh Patel (9408033391) |
| G-04 | Physical Hostel & Transport Fees | On-campus hostel room rates and transportation bus fees (Online degree programmes are 100% distance/online and do not bundle physical campus accommodation or transport). | `Admissions` | Mr. Darshit Patel (7434055553) |
| G-05 | Degree Convocation Ceremony Dates | Exact dates and physical venue booking for the annual university degree convocation ceremony. | `Examinations` | Mr. Snehal Patel (9409572216) |

---

## 4. Scraper Analysis & Ingestion Recommendations

### Current Scraper (`scraper.py`) Audit
1. **Dynamic Content Hydration:** The current Playwright scraper fetches `https://charusat.online/` pages. Because modern university portals rely on client-side accordion components (e.g. FAQ accordions and syllabus dropdowns), simple headless page loading without clicking or expanding all accordions can lead to omitted collapsible answers.
2. **Duplicated Sections:** Scraped markdown files (`online_bca.md`, `online_mca.md`) exhibit repeated question sections from shared footer links and template headers.
3. **Table Formats:** HTML `<table>` elements are converted to Markdown tables; when tables are wide or nested, column misalignment can occur.

### Ingestion Improvements (For Future Safe Ingestion)
- **Accordion Auto-Expansion:** In `scraper.py`, execute a page-evaluation script to click `button[aria-expanded="false"]` and `.accordion-toggle` before extracting HTML.
- **Section Deduplication:** Strip boilerplate header/footer navigation links during markdown conversion to avoid vector index dilution.
- **Table Preservation:** Keep Markdown tables intact with explicit markdown header rows (`| Header 1 | Header 2 |`) to enable semantic table parsing in `conflict.py`.
