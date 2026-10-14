# Round 5C FAQ Verification & Grounding Audit

**Audit Date:** 2026-10-14  
**Auditor:** Senior Engineer (RAG Core)  
**Subject:** Rigorous line-by-line verification of `CHANGES/ROUND5B_FAQ_DRAFT.md` (22 benchmark answers) against raw knowledge base files in `backend/knowledge_base/`.

---

## Executive Summary of Audit Findings

Every answer in `CHANGES/ROUND5B_FAQ_DRAFT.md` was checked against raw files using automated and manual text inspection.

1. **Outside Knowledge / Hallucinations Found:**
   - **Q12 (EMI & Installments):** The draft states *"flexible installment and no-cost EMI options are available via university banking partners"*, citing `terms-conditions.md`, Line 42. In raw files, neither "EMI" nor "installment" exists anywhere in `terms-conditions.md` or any PPR PDF. The word matched by regex was `"academic"` (`acad-emi-c year` on line 44). The draft asserted external/outside banking knowledge not present in the CHARUSAT KB.
2. **Misattributed / Conflated Citations Found:**
   - **Q13 (BBA Internship):** Cited `PPR_Online BBA.pdf`, Page 8, Line 76 (`BB606`, 6 Credits). Raw PPR Page 6 actually specifies `OBBA301 Organizational Attachment Programme` (5 Credits). Line 76 actually belongs to `programs/online_bba.md` (`- Organizational Attachment Programme`).
   - **Q14 (MBA Project):** Cited `PPR_Online MBA.pdf`, Page 7, Line 71 (`MB405`, 6 Credits). Raw PPR Page 10 & 12 actually specifies `MBO604 Comprehensive Project - Industrial Training` (8 Credits). Line 71 belongs to `programs/online_mba.md`.
   - **Q15 (MCA Dissertation):** Cited `PPR_Online MCA.pdf`, Page 6, Line 73 (`MC406`, 12 Credits). Raw PPR Page 6 specifies `Dissertation` (Course Code `MC230`, 12 Credits). Line 73 belongs to `programs/online_mca.md`.
   - **Q2 (BCA Eligibility):** Cited `PPR_Online BCA.pdf`, Page 3, Section 2 for `(Science, Commerce, or Arts)`. The raw PPR Page 2/3 merely states `"10+2 or equivalent"`. The specific stream detail `10+2 in any stream, equivalent to all eligible boards (Including NIOS Board)` actually resides on Line 269 of `programs/online_bca.md`.
   - **Q11 (Refund Policy):** Cited `terms-conditions.md`, Line 32. In raw `terms-conditions.md`, section `WITHDRAWALS AND REFUNDS` sits on Line 38-40, stating `"Refund policy as per the University Guidelines."` The actual UGC percentage breakdown (15/30 days) is located in `Fees Refund Policy.pdf` (Page 1).
   - **Q7, Q8, Q9 (PPR Fee Structure Page Numbers):**
     - BCA fee table is on Page 9 & 13 (draft cited Page 10).
     - MBA fee table is on Page 8 (draft cited Page 11).
     - MCA fee table is on Page 8 & 10 (draft cited Page 10).
3. **Verbatim & Highly Grounded Answers Confirmed:**
   - **Q1 (Programmes Offered):** Verbatim across all 4 programme markdown files.
   - **Q16 (Evaluation Splits):** Exact match with raw PPR tables and text across all 4 programmes.
   - **Q17 (WES Recognition):** Verbatim match with `online_bca.md` (Line 285) and `online_mca.md` (Line 259).
   - **Q18 (Webinar Attendance):** Verbatim match with `terms-conditions.md` (Line 24).
   - **Q19–Q22 (KB Gaps & Referrals):** 100% verified against `contact.md` service names, staff names, and phone numbers.

---

## Detailed Item-by-Item Verification Table

| Q# | Topic | Draft Citation (`ROUND5B_FAQ_DRAFT.md`) | Raw File & Actual Location | Status | Audit Findings & Correction |
|:---|:---|:---|:---|:---|:---|
| **Q1** | Online Programmes Offered | `online_bba.md` L.6; `online_bca.md` L.6; `online_mba.md` L.6; `online_mca.md` L.6 | Same files, Line 6 | **VERBATIM** | Accurate titles: Online BBA, Online BCA, Online MBA, Online MCA. |
| **Q2** | BCA Eligibility | `PPR_Online BCA.pdf`, Page 3, Sec. 2 | `PPR_Online BCA.pdf` p.2, 3; `programs/online_bca.md` L.269 | **CONFLATED CITATION** | PPR states "10+2 or equivalent". The stream specification "(Science, Commerce, or Arts / NIOS)" is from `online_bca.md` L.269. |
| **Q3** | BBA Eligibility | `PPR_Online BBA.pdf`, Page 3, Sec. 2 | `PPR_Online BBA.pdf` p.2, 3; `programs/online_bba.md` L.26 | **PARAPHRASE** | PPR states "10+2 or equivalent in any stream". Consistent with raw sources. |
| **Q4** | MBA Eligibility | `PPR_Online MBA.pdf`, Page 3, Sec. 2 | `PPR_Online MBA.pdf` p.2, 3; `programs/online_mba.md` L.26 | **VERBATIM** | Bachelor's degree (min 3 yrs) with at least 50% marks (45% reserved) matches raw text. |
| **Q5** | MCA Eligibility | `PPR_Online MCA.pdf`, Page 3, Sec. 2 | `PPR_Online MCA.pdf` p.2, 3; `programs/online_mca.md` L.26 | **VERBATIM / DOCUMENT CONFLICT** | PPR requires BCA / B.Sc / B.Com / B.A. with Math; note that marketing draft on `online_mca.md` L.14 contains typo "10+2 in any stream". Draft correctly flags this conflict. |
| **Q6** | BBA Total Fee | `PPR_Online BBA.pdf`, Page 10 | `PPR_Online BBA.pdf` p.10 | **VERBATIM** | ₹25,000/sem x 6 = ₹1,50,000 tuition; ₹1,500/sem x 6 = ₹9,000 exam fee; ₹1,59,000 total. |
| **Q7** | BCA Total Fee | `PPR_Online BCA.pdf`, Page 10 | `PPR_Online BCA.pdf` p.9 & 13 | **WRONG PAGE CITATION** | Fee structure table is on Page 9 and Page 13 (Page 10 is evaluation). Amount ₹1,50,000 (₹25,000 x 6) is verified. |
| **Q8** | MBA Total Fee | `PPR_Online MBA.pdf`, Page 11 | `PPR_Online MBA.pdf` p.8; `programs/online_mba.md` L.22 | **WRONG PAGE CITATION / CONFLICT** | PPR Page 8 states ₹40,000/sem x 4 = ₹1,60,000; `online_mba.md` L.22 states ₹75,000/yr (₹1,50,000 total). Citation Page 11 is off by 3. |
| **Q9** | MCA Total Fee | `PPR_Online MCA.pdf`, Page 10 | `PPR_Online MCA.pdf` p.8 | **WRONG PAGE CITATION** | Fee table is on Page 8 (₹35,000/sem x 4 = ₹1,40,000); Page 10 contains institutional budget figures. Amount ₹1,40,000 is verified. |
| **Q10** | Exam Fees & Surcharges | `PPR_Online BBA.pdf` p.10; `PPR_Online BCA.pdf` p.10 | `PPR_Online BBA.pdf` p.10; `PPR_Online BCA.pdf` p.9-10 | **PARAPHRASE** | Exam fee ₹1,500 per semester confirmed. PPR explicitly specifies semester examination fees. |
| **Q11** | Fee Refund Policy | `terms-conditions.md`, Line 32 | `terms-conditions.md` L.38-40; `Fees Refund Policy.pdf` p.1 | **MISATTRIBUTED CITATION** | `terms-conditions.md` L.40 states "Refund policy as per University Guidelines". The detailed sliding scale (100% to 0%) resides in `Fees Refund Policy.pdf` p.1. |
| **Q12** | EMI / Installments | `terms-conditions.md`, Line 42 | *None in raw KB* | **OUTSIDE KNOWLEDGE / FABRICATED CITATION** | "EMI" and "installment" do NOT exist in raw markdown or PDF files. Draft matched `acad-emi-c year` on L.44 and introduced outside assertions regarding "no-cost EMI with banking partners". |
| **Q13** | BBA Internship / Project | `PPR_Online BBA.pdf`, Page 8, Line 76 | `PPR_Online BBA.pdf` p.6; `programs/online_bba.md` L.76 | **CONFLATED CITATION** | Raw PPR Page 6 lists `OBBA301 Organizational Attachment Programme` (5 Credits). Code `BB606` and Line 76 were conflated with `online_bba.md` L.76. |
| **Q14** | MBA Internship / Project | `PPR_Online MBA.pdf`, Page 7, Line 71 | `PPR_Online MBA.pdf` p.10, 12; `programs/online_mba.md` L.71 | **CONFLATED CITATION** | Raw PPR lists `MBO604 Comprehensive Project - Industrial Training` (8 Credits). Draft invented code `MB405` (6 Credits) and conflated Line 71 of `online_mba.md`. |
| **Q15** | MCA Dissertation / Project | `PPR_Online MCA.pdf`, Page 6, Line 73 | `PPR_Online MCA.pdf` p.6; `programs/online_mca.md` L.73 | **CONFLATED CITATION** | Raw PPR p.6 lists `Dissertation` (12 Credits). Line 73 was conflated with `online_mca.md` L.73. Code `MC406` was invented. |
| **Q16** | Evaluation Weightage Splits | `PPR_Online BCA.pdf` pp.6 & 10; `PPR_Online MBA.pdf` p.6; `PPR_Online BBA.pdf` p.8; `PPR_Online MCA.pdf` pp.4-6 | Same PPR files and pages | **VERBATIM** | 100% accurate. Surfaces BCA 50/50 vs 30/70 internal conflict, MBA 50/50, BBA 30/70, MCA 30/70. |
| **Q17** | WES Foreign Equivalence | `online_bca.md`, Line 285; `online_mca.md`, Line 259 | Same files and lines | **VERBATIM** | Verbatim text: "Yes. At Charusat, obtaining a WES evaluation is a streamlined process..." |
| **Q18** | Mandatory Live Webinars | `terms-conditions.md`, Line 24 | `terms-conditions.md`, Line 24 | **VERBATIM** | Verbatim: "Attendance at this live webinar is mandatory and will be monitored and tracked for our records." |
| **Q19** | Specific Faculty Members | `contact.md` Course Mentor | `knowledge_base/contact.md` L.12-14 | **VERBATIM ROUTING** | Honest refusal for gap; routed to Course Mentor: Dr. Hetal Barad (7434055556). |
| **Q20** | Fall 2026 Deadlines | `contact.md` Admissions | `knowledge_base/contact.md` L.4-6 | **VERBATIM ROUTING** | Honest refusal for gap; routed to Admissions: Mr. Darshit Patel (7434055553), Mr. Kirti Patel (7600257365). |
| **Q21** | Upcoming Placement Drives | `contact.md` Student Services | `knowledge_base/contact.md` L.7-8 | **VERBATIM ROUTING** | Honest refusal for gap; routed to Student Services: Mr. Mitesh Patel (9408033391). |
| **Q22** | Hostel & Transport Costs | `contact.md` Admissions | `knowledge_base/contact.md` L.4-6 | **VERBATIM ROUTING** | Honest refusal for gap; routed to Admissions: Mr. Darshit Patel (7434055553), Mr. Kirti Patel (7600257365). |

---

## Actionable Recommendations for System Ingestion

1. **Do NOT ingest Q12 as written:** Because no official EMI or bank financing documentation exists in the raw KB, the RAG chatbot must give an honest refusal for EMI/loan queries and route the user to Accounts & Payments (`Mr. Brijesh Patel / 9408135558`) rather than inventing bank partnerships.
2. **Harmonize Course Codes in Curriculum FAQ:** Replace draft course codes (`BB606`, `MB405`, `MC406`) with official PPR course codes (`OBBA301`, `MBO604`, `MC230`) and accurate credit counts (5, 8, 12).
3. **Correct Document Cross-References:** Explicitly cross-cite `Fees Refund Policy.pdf` alongside `terms-conditions.md` to prevent false conflicts during retrieval of withdrawal percentages.
