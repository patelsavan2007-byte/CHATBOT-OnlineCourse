# Round 5C: Failure Analysis of the 27 WRONG_DATA_EXISTS Audit Results

**Date:** 2026-10-14  
**Source Audit:** `CHANGES/round5b_final_audit.json`  
**Total Failures Analyzed:** 27  

---

## 1. Summary Count by Root Cause

| Cause Code | Description | Count | Percentage |
|:---|:---|:---:|:---:|
| **(A)** | Right chunk not retrieved (retrieval / BM25 / embedding query gap) | **5** | 18.5% |
| **(B)** | Chunk retrieved but model missed it | **0** | 0.0% |
| **(C)** | Wrong topic/programme detected (context inheritance collision) | **1** | 3.7% |
| **(D)** | Chunk cut by context budget | **0** | 0.0% |
| **(E)** | Number/grounding check blocked a correct answer | **0** | 0.0% |
| **(F)** | KB sources conflict (differing official documents) | **1** | 3.7% |
| **(G1)**| Honest refusal for unstated fact, misclassified due to missing ID in audit list | **5** | 18.5% |
| **(G2)**| Complete/correct answer given, but appended `[[MISSING:]]` marker triggered refusal check in audit | **15** | 55.6% |
| **Total** | | **27** | **100.0%** |

---

## 2. Detailed 27-Row Failure Analysis Table

| # | QID | Index | Question | Topic Detected | Programme Detected | Latency (s) | Raw KB Source & Excerpt | Root Cause Code | What Bot Did Wrong / Detailed Explanation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Q04 | 4 | Is the online degree equivalent to a regular degree? | `general` | None | 1.44 | **Absent from KB**. Documents state "10+2 or equivalent" for eligibility, but degree equivalence is not stated. | **(G1)** | Bot gave honest refusal with admissions contact. Audit script misclassified as WRONG_DATA_EXISTS because Q04 was omitted from `known_refusals`. |
| 2 | Q07 | 7 | What documents are required for admission? | `admission` | None | 24.59 | `programs/online_bca.md:38-55` & `online_mca.md:38-55` (Identity, address proof, marksheets). | **(G2)** | Bot listed all mandatory documents for BCA/MCA correctly, but appended `[[MISSING: BBA/MBA]]` note which triggered refusal classification. |
| 3 | Q16 | 16 | Will exams be online or offline? | `exams_grading` | None | 24.25 | `PPR_Online BCA.pdf p.8` & `terms-conditions.md:24` (Online mode via LMS, 2-day window). | **(G2)** | Bot correctly answered "online" with 2-day window, but appended missing marker on practicals, triggering refusal classification. |
| 4 | Q17 | 17 | What is the attendance requirement? | `attendance` | None | 21.01 | `terms-conditions.md:24`: "Attendance at this live webinar is mandatory and will be monitored and tracked for our records." | **(A)** | Right chunk from `terms-conditions.md` was not retrieved; only program PPR PDFs were retrieved. |
| 5 | Q19 | 19 | Are placement assistance services available? | `placement` | None | 18.54 | `PPR_Online BCA.pdf p.13` & `PPR_Online MCA.pdf p.10`: "Placement cell facilitates interviews with reputed IT firms." | **(A)** | Specific placement cell chunks were ranked below general curriculum chunks; bot returned refusal. |
| 6 | Q20 | 20 | Will I receive a degree certificate after completion? | `certificate` | None | 21.45 | `PPR_Online BCA.pdf p.9`: "Award of Degree... upon earning required credits". | **(G2)** | Bot answered YES and quoted credit completion criteria, but appended missing marker on delivery method, triggering refusal classification. |
| 7 | Q21 | 21 | What is the total course fee? | `fees` | None | 45.58 | `programs/online_bba.md:28`, `online_bca.md:32`, `online_mba.md:28`, `online_mca.md:28`. | **(C)** | Chat turn inherited Online BBA from previous query instead of treating general "total fee" query as comparative across all 4 programmes. |
| 8 | Q22 | 22 | What is the semester-wise fee? | `fees` | None | 46.38 | `programs/online_bba.md:28`: Published as Annual Fee (₹50,000) + Semester Exam Fee (₹1,500). | **(G2)** | Bot correctly explained that fees are published year-wise rather than semester-wise, but appended missing marker triggering refusal classification. |
| 9 | Q23 | 23 | Is there any registration or application fee? | `admission` | None | 23.35 | **Absent from KB**. No registration/application fee is published. | **(G1)** | Bot gave honest refusal. Misclassified as WRONG_DATA_EXISTS because Q23 was not in `known_refusals`. |
| 10 | Q28 | 28 | Is GST included in the course fee? | `taxes_hidden_charges` | None | 1.54 | **Absent from KB**. GST / taxes are not mentioned on student fee tables. | **(G1)** | Bot gave honest refusal. Misclassified as WRONG_DATA_EXISTS because Q28 was not in `known_refusals`. |
| 11 | Q29 | 29 | Are examination fees included in the tuition fee? | `fees` | None | 8.89 | `programs/online_bba.md:28`: Lists Exam Fee (₹1,500/sem) separate from Programme Fee. | **(G2)** | Bot accurately answered "No, examination fees are not included", but appended missing marker for other programmes, triggering refusal classification. |
| 12 | Q30 | 30 | Are there any hidden charges? | `taxes_hidden_charges` | None | 45.28 | **Absent from KB**. "Hidden charges" do not exist; brochures state all fees. | **(G2)** | Bot answered that documents do not mention hidden charges and listed published fees, but appended missing marker, triggering refusal classification. |
| 13 | Q32 | 32 | Is there any late fee for delayed payment? | `fees` | None | 21.34 | **Absent from KB**. Late payment fees are not specified. | **(G1)** | Bot gave honest refusal. Misclassified as WRONG_DATA_EXISTS because Q32 was not in `known_refusals`. |
| 14 | Q33 | 33 | Can I pay the fee semester-wise instead of annually? | `fees` | None | 22.54 | `terms-conditions.md:8-12` mentions semester-wise, but program brochures state annual. | **(G2)** | Bot accurately explained the annual brochure structure and conflict, but appended missing marker, triggering refusal classification. |
| 15 | Q34 | 34 | Will I receive a fee receipt after payment? | `fees` | None | 22.34 | `terms-conditions.md:12`: "confirmation of payment upon receipt of fees". | **(A)** | `terms-conditions.md` payment clause was ranked below general fee tables; bot returned refusal. |
| 16 | Q35 | 35 | Is the fee refundable after classes begin? | `refund` | None | 23.05 | `Fees Refund Policy.pdf p.1` (0% after class starts) vs `terms-conditions.md` (pro-rata). | **(F)** | KB documents contradict each other; bot explained pro-rata policy, but appended missing marker, triggering refusal classification. |
| 17 | Q38 | 38 | Who are the faculty members? | `faculty` | None | 27.28 | `online_bba.md:65`, `online_bca.md:85`, `online_mba.md:75` (MCA faculty missing in raw md). | **(G2)** | Bot listed all faculty for BBA, BCA, MBA accurately and noted MCA is absent; missing marker triggered refusal classification. |
| 18 | Q39 | 39 | Will I receive study materials? | `general` | None | 21.60 | `ciqa.md:15` & `terms-conditions.md:8` (e-books, e-materials, e-resources via LMS). | **(G2)** | Bot accurately answered that digital e-resources/e-books are provided via LMS/library, but appended missing marker on physical delivery. |
| 19 | Q45 | 45 | How is the grading system structured? | `exams_grading` | None | 24.08 | `PPR_Online BBA.pdf p.8`, `PPR_Online BCA.pdf p.11`, `PPR_Online MBA.pdf p.7`. | **(G2)** | Bot detailed the 10-point scale and SGPA formula accurately, but appended missing marker on letter grade intervals, triggering refusal classification. |
| 20 | Q46 | 46 | Which Learning Management System (LMS) is used? | `lms_technical` | None | 23.30 | `home.md:42`: "Robust Learning Management System (LMS)" (vendor name not stated). | **(G2)** | Bot accurately described the LMS and noted the software brand is unmentioned; missing marker triggered refusal classification. |
| 21 | Q48 | 48 | What if I forget my LMS password? | `exams_grading` | None | 12.69 | `terms-conditions.md:16` (confidentiality of Access Credentials, prompt notification). | **(G2)** | Bot accurately cited credential confidentiality from terms-conditions.md, but appended missing marker on self-reset link. |
| 22 | Q49 | 49 | Can I attend classes on my mobile phone? | `attendance` | None | 21.31 | `terms-conditions.md:24` (access course materials online and attend virtual classrooms). | **(G2)** | Bot accurately quoted virtual classroom access from anywhere, but appended missing marker on mobile phone testing, triggering refusal classification. |
| 23 | Q50 | 50 | Is there a dedicated mobile app? | `mobile` | None | 23.06 | **Absent from KB**. Mentions "Mobile Applications" as BCA subject, but no app exists. | **(G1)** | Bot gave honest refusal with LMS contact. Misclassified because Q50 was not in `known_refusals`. |
| 24 | Q74 | 74 | What are the student support timings? | `student_support` | None | 6.80 | **Absent from KB**. `contact.md` gives phone numbers but no office timings. | **(G1)** | Bot gave honest refusal with Student Services contact. Misclassified because Q74 was not in `known_refusals`. |
| 25 | Q75 | 75 | Can I raise queries through email or WhatsApp? | `student_support` | None | 3.53 | `programs/online_bca.md:52` & `contact.md` (phone and email listed; WhatsApp unmentioned). | **(G2)** | Bot cited official email/SMS/phone communication modes, but appended missing marker on WhatsApp, triggering refusal classification. |
| 26 | Q76 | 76 | How can I download my marksheet? | `exams_grading` | None | 1.88 | `PPR_Online BCA.pdf p.12` & `PPR_Online MCA.pdf p.10` (evaluation results/transcripts on portal). | **(A)** | Transcript/portal chunks were ranked below general grading chunks; bot returned refusal. |
| 27 | Q77 | 77 | How do I obtain my degree certificate after completion? | `certificate` | None | 2.87 | `PPR_Online BCA.pdf p.9` (degree awarded upon completion of credits). | **(A)** | Award of degree section in PPR PDFs was not retrieved for "obtain certificate"; bot returned refusal. |

---

## 3. Analysis of Questions Transitioning from `CORRECT_REFUSAL` to Answered

The baseline audit recorded 18 `CORRECT_REFUSAL` results; the final audit recorded 15. The questions that transitioned to answered classifications were:

1. **Q24 ("Can I pay the fees in installments?"):**
   - **Answer Given:** Explained fee structure and noted third-party loan / banking assistance in terms.
   - **KB Status:** **GROUNDED** (`terms-conditions.md:8-12`).

2. **Q53 ("Who should I contact if I face technical issues?"):**
   - **Answer Given:** Dumped an unrelated excerpt from `PPR_Online MCA.pdf p.1` ("The online MCA program offers a flexible and accessible platform...").
   - **KB Status:** **INVENTED / UNGROUNDED**. Under Groq token exhaustion, the local fallback `_general_extract()` dumped the first 6 lines of the top chunk instead of returning `NOT_FOUND_ANSWER` or routing to LMS contacts.

3. **Q59 ("Are resume-building workshops conducted?"):**
   - **Answer Given:** Dumped BBA programme structure excerpt ("The structure of BBA programme is as shown in the following figure: Programme Credits...").
   - **KB Status:** **INVENTED / UNGROUNDED**. Resume workshops are absent from the KB; fallback dumped unrelated chunk.

4. **Additional Unprompted Transitions (Q62, Q65, Q67, Q71):**
   - **Q62 ("When does admission start?"):** Dumped admission cancellation clause (`Fees Refund Policy.pdf`). **UNGROUNDED**.
   - **Q65 ("How long does admission approval take?"):** Dumped 10+2 eligibility text. **UNGROUNDED**.
   - **Q67 ("Can I change my course after admission?"):** Dumped Terms & Conditions modification text. **UNGROUNDED**.
   - **Q71 ("Will I get a student ID card?"):** Dumped MCA program overview. **UNGROUNDED**.

### Key Takeaway for Step 2
The single largest reason for `WRONG_DATA_EXISTS` is **Cause G2 (15/27 = 55.6%)**: the model provides a thorough, correct answer, but because it also appended `[[MISSING: ...]]` for a minor absent nuance, `rag_chain.py` injected `"I couldn't find information regarding ... in the official programme documents."`, causing the audit classifier to mislabel the entire answer as a refusal!
The second largest reason is **Cause A (5/27 = 18.5%)**: missing retrieval of `terms-conditions.md` clauses and placement/transcript sections.
The third reason is **Cause G1 (5/27 = 18.5%)**: honest refusals for questions genuinely absent from the KB that were omitted from `known_refusals`.
Finally, `_fallback_generate()` in `backend/app/llm.py` must NEVER dump random chunks when a question is ungrounded; it must return `NOT_FOUND_ANSWER` so the system cleanly refuses.
