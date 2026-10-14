# ROUND 5B BASELINE AUDIT — CHARUSAT Chatbot

**Date:** 2026-10-14  
**Method:** Real live HTTP requests through `POST /api/chat` on the running FastAPI server (`uvicorn api:app --port 8000`).  
**Chat Mode:** Single continuous guest session with sliding window history (last 8 messages) in exact docx question sequence (Q1 to Q77).  

---

## 1. Measured Baseline Summary

| Classification | Count | Description |
|---|---|---|
| **CORRECT** | 26 | Answered accurately from knowledge base |
| **CORRECT_REFUSAL** | 18 | Information not in documents, accurately refused with contact |
| **WRONG_DATA_EXISTS** | 30 | Information exists in KB documents but was refused or incomplete |
| **ERROR (Timeout)** | 3 | Requests timed out during dense sequential retrieval (Q12-Q14) |
| **Total** | 77 | Complete docx question set |

---

## 2. Seed Facts Re-Verification (Ground Truth from Raw KB Files)

| Fact | Document Source | Location / Citation | Verified Value |
|---|---|---|---|
| **Internship / Project** | `online_bba.md`, `online_mba.md`, `online_mca.md` | Lines 76, 71, 73 | BBA: Organizational Attachment Programme; MBA: Comprehensive Project - Industrial Training; MCA: Dissertation / Project Work - Industrial Training |
| **WES Evaluation** | `online_bca.md`, `online_mca.md` | FAQs (line 285, 259) | Explicitly supported via portal/email |
| **Live Webinar Attendance** | `terms-conditions.md` | Line 24 | Mandatory and tracked for records |
| **BBA Exam Fee & Total** | `PPR_Online BBA.pdf` | Page 10 | Exam fee: Rs.1,500/sem (Rs.9,000 total); Total programme cost: Rs.1,59,000 |
| **BCA Evaluation Conflict** | `PPR_Online BCA.pdf` | Text p.10 vs Table p.6 | Real intra-doc conflict: 50/50 in text vs 30/70 in course tables |
| **MBA Evaluation** | `PPR_Online MBA.pdf` | Page 6 | 50% internal / 50% external |
| **BBA Evaluation** | `PPR_Online BBA.pdf` | Page 8 | 30% internal / 70% external |
| **MCA Evaluation** | `PPR_Online MCA.pdf` | Pages 4-6 | 30% internal / 70% external |
| **BBA Credits Conflict** | `PPR_Online BBA.pdf` | Page 4, 6, 9 | p.4 & p.6: 130 credits; p.9: 120 credits |
| **MBA Credits Conflict** | `PPR_Online MBA.pdf` | Page 4, 10, 12 | p.4 & p.10: 102 credits; p.12: 100 credits |
| **MCA 10+2 Copy Error** | `online_mca.md` | FAQ section | Incorrectly states 10+2 eligibility under MCA FAQ |
| **BBA Grade Ranges Gaps**| `PPR_Online BBA.pdf` | Page 9 | Gaps between 94-96% (Grade O >=96 vs A+ <95) and 35-36% (Pass >=36 vs Fail <35) |
| **Document List Coverage**| `online_bca.md`, `online_mca.md` | FAQ section | Listed for BCA & MCA; missing from BBA & MBA FAQs |

---

## 3. Question-by-Question Baseline Audit Log

| # | ID | Category | Question | Standalone Question | Topic | Classification | Elapsed |
|---|---|---|---|---|---|---|---|
| 1 | Q01 | General Questions | What online programs are offered? | What online programs are offered? | general | **CORRECT** | 0.06s |
| 2 | Q02 | General Questions | Is the online degree recognized by UGC? | Is the online degree recognized by UGC? | general | **CORRECT** | 0.11s |
| 3 | Q03 | General Questions | Is the degree valid for government and private jobs? | Is the degree valid for government and private jobs? | career | **CORRECT_REFUSAL** | 1.5s |
| 4 | Q04 | General Questions | Is the online degree equivalent to a regular degree? | Is the online degree equivalent to a regular degree? | career | **WRONG_DATA_EXISTS** | 4.05s |
| 5 | Q05 | General Questions | Who is eligible for this program? | Who is eligible for this program? | eligibility | **CORRECT** | 0.06s |
| 6 | Q06 | General Questions | What is the admission process? | What is the admission process? | admission | **CORRECT** | 0.08s |
| 7 | Q07 | General Questions | What documents are required for admission? | What documents are required for admission? | admission | **WRONG_DATA_EXISTS** | 0.22s |
| 8 | Q08 | General Questions | Is there an entrance exam? | Is there an entrance exam? | grading | **CORRECT_REFUSAL** | 0.96s |
| 9 | Q09 | General Questions | What is the duration of the program? | What is the duration of the program? | duration | **CORRECT** | 0.79s |
| 10 | Q10 | General Questions | Can I study while working? | Can I study while working? | duration | **CORRECT** | 2.31s |
| 11 | Q11 | General Questions | Are live classes compulsory? | Are live classes compulsory? | general | **WRONG_DATA_EXISTS** | 9.97s |
| 12 | Q12 | General Questions | Are classes recorded? | Are classes recorded? | general | **ERROR** | 60.02s |
| 13 | Q13 | General Questions | Can I access recorded lectures anytime? | Can I access recorded lectures anytime? | general | **ERROR** | 60.01s |
| 14 | Q14 | General Questions | What is the class schedule? | What is the class schedule? | general | **ERROR** | 60.01s |
| 15 | Q15 | General Questions | How are examinations conducted? | How are examinations conducted? | grading | **CORRECT** | 33.41s |
| 16 | Q16 | General Questions | Will exams be online or offline? | Will exams be online or offline? | grading | **CORRECT** | 11.72s |
| 17 | Q17 | General Questions | What is the attendance requirement? | What is the attendance requirement? | eligibility | **WRONG_DATA_EXISTS** | 14.35s |
| 18 | Q18 | General Questions | Is there any internship included? | Is there any internship included? | eligibility | **WRONG_DATA_EXISTS** | 20.27s |
| 19 | Q19 | General Questions | Are placement assistance services available? | Are placement assistance services available? | career | **WRONG_DATA_EXISTS** | 0.81s |
| 20 | Q20 | General Questions | Will I receive a degree certificate after completion? | Will I receive a degree certificate after completion? | career | **WRONG_DATA_EXISTS** | 10.5s |
| 21 | Q21 | Fees Related Questions | What is the total course fee? | What is the total course fee? | fees | **CORRECT** | 11.13s |
| 22 | Q22 | Fees Related Questions | What is the semester-wise fee? | What is the semester-wise fee? | fees | **WRONG_DATA_EXISTS** | 26.45s |
| 23 | Q23 | Fees Related Questions | Is there any registration or application fee? | Is there any registration or application fee? | fees | **CORRECT_REFUSAL** | 24.55s |
| 24 | Q24 | Fees Related Questions | Can I pay the fees in installments? | Can I pay the fees in installments? | fees | **CORRECT_REFUSAL** | 20.35s |
| 25 | Q25 | Fees Related Questions | What are the available payment modes? | What are the available payment modes? | fees | **WRONG_DATA_EXISTS** | 7.92s |
| 26 | Q26 | Fees Related Questions | Are EMI options available? | Are EMI options available? | fees | **CORRECT_REFUSAL** | 0.41s |
| 27 | Q27 | Fees Related Questions | Are there any scholarships or fee concessions? | Are there any scholarships or fee concessions? | fees | **CORRECT_REFUSAL** | 7.73s |
| 28 | Q28 | Fees Related Questions | Is GST included in the course fee? | Is GST included in the course fee? | fees | **CORRECT_REFUSAL** | 8.23s |
| 29 | Q29 | Fees Related Questions | Are examination fees included in the tuition fee? | Are examination fees included in the tuition fee? | fees | **CORRECT** | 8.52s |
| 30 | Q30 | Fees Related Questions | Are there any hidden charges? | Are there any hidden charges? | fees | **CORRECT_REFUSAL** | 0.4s |
| 31 | Q31 | Fees Related Questions | What is the refund policy if I cancel my admission? | What is the refund policy if I cancel my admission? | admission | **CORRECT** | 20.03s |
| 32 | Q32 | Fees Related Questions | Is there any late fee for delayed payment? | Is there any late fee for delayed payment? | fees | **CORRECT_REFUSAL** | 19.08s |
| 33 | Q33 | Fees Related Questions | Can I pay the fee semester-wise instead of annually? | Can I pay the fee semester-wise instead of annually? | fees | **CORRECT** | 8.5s |
| 34 | Q34 | Fees Related Questions | Will I receive a fee receipt after payment? | Will I receive a fee receipt after payment? | fees | **CORRECT** | 20.48s |
| 35 | Q35 | Fees Related Questions | Is the fee refundable after classes begin? | Is the fee refundable after classes begin? | fees | **WRONG_DATA_EXISTS** | 9.27s |
| 36 | Q36 | Academic Questions | What subjects are covered in the program? | What subjects are covered in the program? | subjects | **CORRECT** | 9.2s |
| 37 | Q37 | Academic Questions | How many semesters does the course have? | How many semesters does the course have? | duration | **CORRECT** | 22.79s |
| 38 | Q38 | Academic Questions | Who are the faculty members? | Who are the faculty members? | duration | **CORRECT** | 12.2s |
| 39 | Q39 | Academic Questions | Will I receive study materials? | Will I receive study materials? | general | **CORRECT** | 10.83s |
| 40 | Q40 | Academic Questions | Are e-books provided? | Are e-books provided? | general | **WRONG_DATA_EXISTS** | 9.37s |
| 41 | Q41 | Academic Questions | How are assignments submitted? | How are assignments submitted? | general | **WRONG_DATA_EXISTS** | 10.19s |
| 42 | Q42 | Academic Questions | How much weightage do assignments carry? | How much weightage do assignments carry? | general | **WRONG_DATA_EXISTS** | 8.38s |
| 43 | Q43 | Academic Questions | What is the passing criteria? | What is the passing criteria? | eligibility | **WRONG_DATA_EXISTS** | 10.92s |
| 44 | Q44 | Academic Questions | Can I appear for backlogs online? | Can I appear for backlogs online? | eligibility | **WRONG_DATA_EXISTS** | 6.27s |
| 45 | Q45 | Academic Questions | How is the grading system structured? | How is the grading system structured? | grading | **CORRECT** | 23.58s |
| 46 | Q46 | Technical Questions | Which Learning Management System (LMS) is used? | Which Learning Management System (LMS) is used? | lms | **WRONG_DATA_EXISTS** | 13.51s |
| 47 | Q47 | Technical Questions | How do I log in to the LMS? | How do I log in to the LMS? | lms | **WRONG_DATA_EXISTS** | 11.41s |
| 48 | Q48 | Technical Questions | What if I forget my LMS password? | What if I forget my LMS password? | lms | **WRONG_DATA_EXISTS** | 14.24s |
| 49 | Q49 | Technical Questions | Can I attend classes on my mobile phone? | Can I attend classes on my mobile phone? | contact | **CORRECT** | 16.26s |
| 50 | Q50 | Technical Questions | Is there a dedicated mobile app? | Is there a dedicated mobile app? | contact | **CORRECT_REFUSAL** | 6.36s |
| 51 | Q51 | Technical Questions | What internet speed is recommended? | What internet speed is recommended? | general | **WRONG_DATA_EXISTS** | 0.91s |
| 52 | Q52 | Technical Questions | Is technical support available? | Is technical support available? | lms | **CORRECT** | 5.57s |
| 53 | Q53 | Technical Questions | Who should I contact if I face technical issues? | Who should I contact if I face technical issues? | contact | **CORRECT_REFUSAL** | 0.46s |
| 54 | Q54 | Career & Placement Questions | Does the university provide placement assistance? | Does the university provide placement assistance? | career | **CORRECT** | 6.18s |
| 55 | Q55 | Career & Placement Questions | Are internships available? | Are internships available? | career | **CORRECT** | 4.41s |
| 56 | Q56 | Career & Placement Questions | Can I pursue higher education after completing this program? | Can I pursue higher education after completing this program? | general | **WRONG_DATA_EXISTS** | 8.5s |
| 57 | Q57 | Career & Placement Questions | Is the degree accepted abroad? | Is the degree accepted abroad? | general | **WRONG_DATA_EXISTS** | 19.52s |
| 58 | Q58 | Career & Placement Questions | Will there be career guidance sessions? | Will there be career guidance sessions? | career | **WRONG_DATA_EXISTS** | 7.43s |
| 59 | Q59 | Career & Placement Questions | Are resume-building workshops conducted? | Are resume-building workshops conducted? | career | **CORRECT_REFUSAL** | 6.32s |
| 60 | Q60 | Career & Placement Questions | Will there be mock interviews? | Will there be mock interviews? | general | **WRONG_DATA_EXISTS** | 0.85s |
| 61 | Q61 | Career & Placement Questions | Do companies recruit online degree students? | Do companies recruit online degree students? | career | **WRONG_DATA_EXISTS** | 12.84s |
| 62 | Q62 | Admission Questions | When does admission start? | When does admission start? | admission | **CORRECT_REFUSAL** | 8.42s |
| 63 | Q63 | Admission Questions | What is the last date to apply? | What is the last date to apply? | admission | **WRONG_DATA_EXISTS** | 18.21s |
| 64 | Q64 | Admission Questions | Can I apply online? | Can I apply online? | admission | **CORRECT** | 8.3s |
| 65 | Q65 | Admission Questions | How long does admission approval take? | How long does admission approval take? | admission | **CORRECT_REFUSAL** | 9.26s |
| 66 | Q66 | Admission Questions | How will I know if my admission is confirmed? | How will I know if my admission is confirmed? | admission | **CORRECT** | 11.38s |
| 67 | Q67 | Admission Questions | Can I change my course after admission? | Can I change my course after admission? | admission | **CORRECT_REFUSAL** | 8.28s |
| 68 | Q68 | Admission Questions | Can international students apply? | Can international students apply? | admission | **CORRECT_REFUSAL** | 7.69s |
| 69 | Q69 | Admission Questions | Is there any age limit for admission? | Is there any age limit for admission? | admission | **CORRECT** | 9.4s |
| 70 | Q70 | Student Support Questions | Is academic counseling available? | Is academic counseling available? | admission | **WRONG_DATA_EXISTS** | 9.13s |
| 71 | Q71 | Student Support Questions | Will I get a student ID card? | Will I get a student ID card? | general | **CORRECT_REFUSAL** | 18.22s |
| 72 | Q72 | Student Support Questions | How can I contact faculty members? | How can I contact faculty members? | contact | **WRONG_DATA_EXISTS** | 11.29s |
| 73 | Q73 | Student Support Questions | Is there a dedicated student support team? | Is there a dedicated student support team? | contact | **CORRECT** | 18.54s |
| 74 | Q74 | Student Support Questions | What are the student support timings? | What are the student support timings? | general | **CORRECT_REFUSAL** | 7.33s |
| 75 | Q75 | Student Support Questions | Can I raise queries through email or WhatsApp? | Can I raise queries through email or WhatsApp? | contact | **WRONG_DATA_EXISTS** | 2.13s |
| 76 | Q76 | Student Support Questions | How can I download my marksheet? | How can I download my marksheet? | contact | **WRONG_DATA_EXISTS** | 1.05s |
| 77 | Q77 | Student Support Questions | How do I obtain my degree certificate after completion? | How do I obtain my degree certificate after completion? | general | **WRONG_DATA_EXISTS** | 8.3s |
