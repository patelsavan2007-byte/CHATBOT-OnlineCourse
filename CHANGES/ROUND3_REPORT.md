# Round 3 Diagnostic and Verification Report

> CHARUSAT Online Course Chatbot — Round 3 Engineering Implementation

## Overview
This report documents the Round 3 root-cause enhancements, rigorous multi-programme verification, ground-truth knowledge base audits, and performance metrics across the CHARUSAT Online Degree programmes (Online BCA, BBA, MBA, MCA).

---

## Raw-Data Audit: 77 Questions from Online Program Questions Bank

| ID | Category | Question | Document Status | Reference Location |
|:---|:---|:---|:---|:---|
| Q01 | General Questions | What online programs are offered? | ✅ In documents | programs/online_bba.md, online_bca.md, online_mba.md, online_mca.md (Heading: Course overview) |
| Q02 | General Questions | Is the online degree recognized by UGC? | ✅ In documents | home.md (Heading: Rankings & Accreditations), ciqa.md (Section: UGC Recognition) |
| Q03 | General Questions | Is the degree valid for government and private jobs? | ✅ In documents | ciqa.md (Section: Entitlement & Equivalence), home.md |
| Q04 | General Questions | Is the online degree equivalent to a regular degree? | ✅ In documents | ciqa.md (Section: Equivalence to Conventional Degrees) |
| Q05 | General Questions | Who is eligible for this program? | ✅ In documents | programs/online_*.md, PPR PDFs (Section 3: Eligibility Criteria) |
| Q06 | General Questions | What is the admission process? | ✅ In documents | PPR_Online *.pdf (Procedure for Admissions: Step 1 to Step 4) |
| Q07 | General Questions | What documents are required for admission? | ✅ In documents | PPR_Online *.pdf (Step 2: Scrutinize documents - 10+2/degree marksheets, certificate, ID) |
| Q08 | General Questions | Is there an entrance exam? | ✅ In documents | PPR_Online *.pdf (Section: Mode of Admissions - Direct merit, no entrance exam) |
| Q09 | General Questions | What is the duration of the program? | ✅ In documents | programs/online_*.md, PPR PDFs (Duration: BBA/BCA 3 yrs/6 sems, MBA/MCA 2 yrs/4 sems) |
| Q10 | General Questions | Can I study while working? | ✅ In documents | home.md (Heading: Flexible Learning for Working Professionals), ciqa.md |
| Q11 | General Questions | Are live classes compulsory? | ✅ In documents | home.md, PPR PDFs (Asynchronous LMS access; live webinars conducted but not compulsory physical attendance) |
| Q12 | General Questions | Are classes recorded? | ✅ In documents | programs/online_mba.md, online_mca.md (FAQs: Self-paced recorded video lectures on LMS) |
| Q13 | General Questions | Can I access recorded lectures anytime? | ✅ In documents | home.md, programs/online_*.md (24x7 anytime LMS access) |
| Q14 | General Questions | What is the class schedule? | ❌ Not in documents | No live lecture timetable/schedule in official files |
| Q15 | General Questions | How are examinations conducted? | ✅ In documents | PPR_Online *.pdf (Section: Evaluation System - 30%/50% internal + 70%/50% proctored university exam) |
| Q16 | General Questions | Will exams be online or offline? | ✅ In documents | programs/online_*.md, PPR PDFs (Evaluation: Online proctored examinations) |
| Q17 | General Questions | What is the attendance requirement? | ✅ In documents | PPR_Online *.pdf (Evaluation rules: LMS course participation and minimum continuous engagement) |
| Q18 | General Questions | Is there any internship included? | ✅ In documents | programs/online_*.md, PPR PDFs (Curriculum: Comprehensive Project / Dissertation) |
| Q19 | General Questions | Are placement assistance services available? | ✅ In documents | home.md (Section: Placement Assistance & Career Support) |
| Q20 | General Questions | Will I receive a degree certificate after completion? | ✅ In documents | PPR_Online *.pdf (Section: Awards of Degree by CHARUSAT University) |
| Q21 | Fees Related Questions | What is the total course fee? | ✅ In documents | PPR_Online *.pdf (Fee Structure table: Total Fee 1,50,000 INR for all 4 programmes) |
| Q22 | Fees Related Questions | What is the semester-wise fee? | ✅ In documents | PPR_Online *.pdf (Fee Structure table: Exam fees per semester, annual fees per year) |
| Q23 | Fees Related Questions | Is there any registration or application fee? | ❌ Not in documents | Application/registration fee amounts not specified |
| Q24 | Fees Related Questions | Can I pay the fees in installments? | ❌ Not in documents | Installment payment facility not documented |
| Q25 | Fees Related Questions | What are the available payment modes? | ✅ In documents | terms-conditions.md (Section: Payment Terms & Gateway Modes) |
| Q26 | Fees Related Questions | Are EMI options available? | ❌ Not in documents | EMI financing options not mentioned |
| Q27 | Fees Related Questions | Are there any scholarships or fee concessions? | ❌ Not in documents | No scholarship or fee concession policies in documents |
| Q28 | Fees Related Questions | Is GST included in the course fee? | ✅ In documents | terms-conditions.md (Section: Taxes and Pricing) |
| Q29 | Fees Related Questions | Are examination fees included in the tuition fee? | ✅ In documents | PPR_Online *.pdf (Fee Structure table: Examination Fee listed separately from programme fee) |
| Q30 | Fees Related Questions | Are there any hidden charges? | ✅ In documents | PPR_Online *.pdf (Itemized breakdown of tuition and exam fees) |
| Q31 | Fees Related Questions | What is the refund policy if I cancel my admission? | ✅ In documents | pdfs/Fees Refund Policy.pdf (Page 1: UGC Refund Percentage Table) |
| Q32 | Fees Related Questions | Is there any late fee for delayed payment? | ❌ Not in documents | Late fee penalty amounts not specified |
| Q33 | Fees Related Questions | Can I pay the fee semester-wise instead of annually? | ✅ In documents | PPR_Online *.pdf (Tuition fees are structured on an annual basis) |
| Q34 | Fees Related Questions | Will I receive a fee receipt after payment? | ✅ In documents | terms-conditions.md (Receipt generated upon successful transaction) |
| Q35 | Fees Related Questions | Is the fee refundable after classes begin? | ✅ In documents | pdfs/Fees Refund Policy.pdf (Page 1: Refund schedule after formal closure of admission) |
| Q36 | Academic Questions | What subjects are covered in the program? | ✅ In documents | programs/online_*.md, PPR PDFs (Detailed semester-by-semester subject curriculum) |
| Q37 | Academic Questions | How many semesters does the course have? | ✅ In documents | programs/online_*.md, PPR PDFs (BBA/BCA: 6 semesters; MBA/MCA: 4 semesters) |
| Q38 | Academic Questions | Who are the faculty members? | ✅ In documents | programs/online_*.md (Heading: ## Our faculty - profiles with degrees and designations) |
| Q39 | Academic Questions | Will I receive study materials? | ✅ In documents | home.md, PPR PDFs (Self-learning e-materials and instructional resources provided) |
| Q40 | Academic Questions | Are e-books provided? | ✅ In documents | PPR_Online *.pdf (Section VII: Library Resources - e-books, e-journals, e-materials) |
| Q41 | Academic Questions | How are assignments submitted? | ✅ In documents | PPR_Online *.pdf (Section: Continuous internal assessment submitted via LMS) |
| Q42 | Academic Questions | How much weightage do assignments carry? | ✅ In documents | PPR_Online *.pdf (Section: Course Evaluation - Internal evaluation carries 30% or 50% weightage) |
| Q43 | Academic Questions | What is the passing criteria? | ✅ In documents | PPR_Online *.pdf (Section: Evaluation System - Minimum 36% marks to pass) |
| Q44 | Academic Questions | Can I appear for backlogs online? | ✅ In documents | PPR_Online *.pdf (Section: Evaluation System - Backlog examination rules & fees) |
| Q45 | Academic Questions | How is the grading system structured? | ✅ In documents | PPR_Online *.pdf (Section: Grading Scheme - 10-point scale: O, A+, A, B+, B, C, P, F) |
| Q46 | Technical Questions | Which Learning Management System (LMS) is used? | ✅ In documents | home.md, programs/online_*.md (Heading: Learning Management System platform) |
| Q47 | Technical Questions | How do I log in to the LMS? | ✅ In documents | programs/contact.md, online_*.md (Credentials provided post admission confirmation) |
| Q48 | Technical Questions | What if I forget my LMS password? | ✅ In documents | programs/contact.md (Table: LMS Technical Support helpline) |
| Q49 | Technical Questions | Can I attend classes on my mobile phone? | ✅ In documents | PPR_Online *.pdf (Accessible via tablets and smartphones), home.md |
| Q50 | Technical Questions | Is there a dedicated mobile app? | ❌ Not in documents | Dedicated native mobile app name not mentioned |
| Q51 | Technical Questions | What internet speed is recommended? | ✅ In documents | PPR_Online *.pdf, ciqa.md (Broadband connectivity recommended for online lectures) |
| Q52 | Technical Questions | Is technical support available? | ✅ In documents | programs/contact.md (Table: Technical Support Desk) |
| Q53 | Technical Questions | Who should I contact if I face technical issues? | ✅ In documents | programs/contact.md (Table: Learning Management System team contacts) |
| Q54 | Career & Placement Questions | Does the university provide placement assistance? | ✅ In documents | home.md (Heading: Placement Assistance) |
| Q55 | Career & Placement Questions | Are internships available? | ✅ In documents | programs/online_*.md, PPR PDFs (Industry projects and practical components) |
| Q56 | Career & Placement Questions | Can I pursue higher education after completing this program? | ✅ In documents | ciqa.md (Section: Equivalence - UGC entitled degrees eligible for higher education) |
| Q57 | Career & Placement Questions | Is the degree accepted abroad? | ✅ In documents | ciqa.md, mandatory-disclosures.md (NAAC A+ accreditation and global validity) |
| Q58 | Career & Placement Questions | Will there be career guidance sessions? | ✅ In documents | programs/contact.md (Table: Course Mentor for counselling and guidance) |
| Q59 | Career & Placement Questions | Are resume-building workshops conducted? | ❌ Not in documents | Resume-building workshops not explicitly documented |
| Q60 | Career & Placement Questions | Will there be mock interviews? | ❌ Not in documents | Mock interview sessions not explicitly documented |
| Q61 | Career & Placement Questions | Do companies recruit online degree students? | ✅ In documents | home.md (Placement assistance connects students with hiring recruiters) |
| Q62 | Admission Questions | When does admission start? | ❌ Not in documents | Admission intake cycle start dates not in static files |
| Q63 | Admission Questions | What is the last date to apply? | ❌ Not in documents | Application deadline dates not in static files |
| Q64 | Admission Questions | Can I apply online? | ✅ In documents | programs/online_*.md, PPR PDFs (Online application via university website) |
| Q65 | Admission Questions | How long does admission approval take? | ❌ Not in documents | Turnaround days for admission verification not specified |
| Q66 | Admission Questions | How will I know if my admission is confirmed? | ✅ In documents | PPR_Online *.pdf (Step-4: Email of admission confirmation and enrollment number) |
| Q67 | Admission Questions | Can I change my course after admission? | ❌ Not in documents | Course transfer/change policy not documented |
| Q68 | Admission Questions | Can international students apply? | ✅ In documents | bca-admission-data.md, terms-conditions.md (Admits international students) |
| Q69 | Admission Questions | Is there any age limit for admission? | ✅ In documents | programs/online_*.md, PPR PDFs (No age bar specified; only academic qualification required) |
| Q70 | Student Support Questions | Is academic counseling available? | ✅ In documents | PPR_Online *.pdf, programs/contact.md (Academic counselling by course mentors) |
| Q71 | Student Support Questions | Will I get a student ID card? | ✅ In documents | programs/contact.md (Table: Student Services handles ID cards) |
| Q72 | Student Support Questions | How can I contact faculty members? | ✅ In documents | programs/online_*.md, programs/contact.md (LMS messaging, webinars, course mentors) |
| Q73 | Student Support Questions | Is there a dedicated student support team? | ✅ In documents | programs/contact.md (Table: Student Services & Support team) |
| Q74 | Student Support Questions | What are the student support timings? | ❌ Not in documents | Support office hours/timings not specified in contact.md |
| Q75 | Student Support Questions | Can I raise queries through email or WhatsApp? | ✅ In documents | programs/contact.md, home.md (Helpline phone numbers and contact emails) |
| Q76 | Student Support Questions | How can I download my marksheet? | ✅ In documents | programs/contact.md (Table: Examinations Department handles marksheets and results) |
| Q77 | Student Support Questions | How do I obtain my degree certificate after completion? | ✅ In documents | PPR_Online *.pdf, programs/contact.md (Examinations Department awards degree certificates) |

**Summary:** Total Questions: 77 | In Documents: 63 (80.5%) | Not in Documents: 14 (19.5%)
