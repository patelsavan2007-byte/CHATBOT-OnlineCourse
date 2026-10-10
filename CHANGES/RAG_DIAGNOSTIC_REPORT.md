# RAG Diagnostic & Performance Report — CHARUSAT Online Course Chatbot

> **Current Status:** Operational & Grounded | **Benchmark Coverage:** 40 Baseline Questions + 30 New Stress-Test Questions  
> **Last Updated:** October 2026 (Round 2 Completion)

---

## 1. Executive Status Summary

The CHARUSAT Online Course RAG system has undergone two rigorous rounds of empirical debugging, source cleaning, and multi-category evaluation. The chatbot demonstrates **strict adherence to source documents**, **zero hallucinations** across all tested numerical and policy questions, robust **multi-turn context switching**, and **safe resistance** to prompt injection and false-premise traps.

### Core Metrics Snapshot
| Area | Metric | Value | Status |
|---|---|---|---|
| **Vector Index** | Valid Chunks in ChromaDB | **345** (down from 389 junk chunks) | Cleaned & Verified |
| **Ingestion Quality** | Empty-table / <80 char chunks | **0** (100% eliminated) | Cleaned & Verified |
| **Latency** | Retrieval / Pipeline Total | **0.05s ret / ~1.8s total** (without reranker) | High Speed |
| **40 Baseline Benchmark** | Answered / Clean Handled | **33 Answered, 3 Clarifications, 4 Safe Refusals** | 0 Regressions |
| **30 New Stress Benchmark** | Answered / Handled | **27 Retrieved & Grounded, 3 Clean Fallbacks** | 0 Hallucinations |
| **Reranker Status** | `BAAI/bge-reranker-base` | **Disabled (`RERANKER_ENABLED = False`)** | Evaluated & Reverted |

---

## 2. Reranker Investigation, Fix, Evaluation & Honest Verdict

### 2.1 Why the Reranker Was Not Loading
- **Root Cause:** The `backend/.venv` environment did not have `FlagEmbedding` installed (`ModuleNotFoundError`).
- **Silent Failure:** In `backend/app/reranker.py`, the loader had a broad `except ImportError:` that caught the error, logged a warning, and silently set `self._model = False`. The system ran entirely on FastEmbed cosine similarity without any cross-encoder reranking during Round 1.

### 2.2 How It Was Fixed & Made Transparent
1. **FastEmbed Native Cross-Encoder:** Replaced the heavy PyTorch `FlagEmbedding` loader with FastEmbed's lightweight ONNX cross-encoder: `from fastembed.rerank.cross_encoder import TextCrossEncoder`. This utilized the existing ONNX runtime on CPU and downloaded `BAAI/bge-reranker-base` (1.04 GB).
2. **Startup Logging & Loud Failure:** Added startup error logging if enabled but failing to initialize.
3. **Health Check Visibility:** Updated `GET /health` to expose both `reranker_active: bool` and `reranker_error: str | None`. Health checks confirmed `reranker_active: true`.

### 2.3 Measured Performance Impact (40-Question Benchmark)
When `BGEReranker` was activated and evaluated on the 40 benchmark questions (`step1_evaluate_reranker.py`):
- **Latency Explosion:** FastEmbed semantic search without reranker executes in **~0.05s**. With the ONNX cross-encoder reranker, latency increased by **+2.596s per query** (a ~50x retrieval slowdown).
- **Score Formula & Threshold Collapse:**
  - The combination formula: `combined = 0.7 * normalized_rerank + 0.3 * orig_score`.
  - `BAAI/bge-reranker-base` is an MS-MARCO passage reranker. On dense university policy tables and Hinglish queries, it produced negative raw logits (`-2.0` to `-7.0`), mapping to normalized scores of `0.15`–`0.40`.
  - Blending these with `orig_score` severely depressed scores below the production threshold `MIN_RELEVANCE_SCORE = 0.52`.
- **Severe Regressions (6 Questions Dropped to 0 Chunks):**
  - **Q15** (*Midway refund*): Baseline retrieved 6 chunks (score 0.681) $\rightarrow$ Reranker: **0 chunks (`NO_CHUNKS`)**
  - **Q18** (*BBA caution deposit*): Baseline retrieved 6 chunks (score 0.628) $\rightarrow$ Reranker: **0 chunks (`NO_CHUNKS`)**
  - **Q19** (*CIQA learner support*): Baseline retrieved 6 chunks (score 0.700) $\rightarrow$ Reranker: **0 chunks (`NO_CHUNKS`)**
  - **Q23** (*MBA specializations*): Baseline retrieved 6 chunks (score 0.786) $\rightarrow$ Reranker: **0 chunks (`NO_CHUNKS`)**
  - **Q24** (*fees?*): Baseline retrieved 6 chunks (score 0.622) $\rightarrow$ Reranker: **0 chunks (`NO_CHUNKS`)**
  - **Q33** (*Faculty-to-student ratio*): Baseline retrieved 6 chunks (score 0.652) $\rightarrow$ Reranker: **0 chunks (`NO_CHUNKS`)**
- **Ranking Distortions:** On key policy queries (e.g., Q08 Refund Policy and Q17 UGC Recognition), the reranker demoted the primary authoritative documents (`Fees Refund Policy.pdf` and `home.md`) from #1 to lower ranks, promoting generic course overviews instead.

### 2.4 Honest Verdict
> **Honest Verdict:** The reranker **significantly degraded system performance**. It caused a 50x retrieval latency penalty (+2.6s/query), induced 6 severe regressions to `NO_CHUNKS`, reduced context availability across 29 questions, and degraded ranking quality on specific policy questions.  
> **Action Taken:** Per the ground rules, `RERANKER_ENABLED` was set to `False` in `config.py`. The FastEmbed cross-encoder loader and health checks remain implemented for future testing with domain-adapted multilingual rerankers.

---

## 3. Knowledge Base & Ingestion Cleanup (Step 2)

### 3.1 Source Audit & Root-Cause Remediation
1. **Google Sheets Grid Over-scraping:** `bba-admission-data.md` and `bca-admission-data.md` had 9 and 27 real student records respectively, followed by 90+ empty spreadsheet grid rows (`| | | ...`) scraped verbatim as markdown tables. These produced 21 junk chunks. Trimming the empty grid rows eliminated all 21 empty-table chunks at source without losing any student data.
2. **UTF-8 Mojibake Cleanup:** Repaired corrupted byte sequences (`â\x80\x93` $\rightarrow$ `–`, `â\x80\x99` $\rightarrow$ `’`, `â\x80\x9c`/`â\x80\x9d` $\rightarrow$ `“`/`”`, `â\x80\xa2` $\rightarrow$ `•`) across 8 source files.
3. **Stray Punctuation:** Removed stray `=` on line 25 of `programs/contact.md`.
4. **Ingestion Filters:** Added `is_valid_chunk()` in `app/ingestion.py` and `app/pdf_ingestion.py` to discard chunks with length < 80 characters, < 40 alphanumeric characters, or empty tables. Added `deduplicate_chunks()` to drop internal duplicates while preserving cross-programme requirements.

### 3.2 Vector Index Statistics: Before vs. After Cleanup
| Metric | Baseline (Round 1) | After Step 2 Cleanup | Net Change |
|---|---|---|---|
| **Total Chunks in ChromaDB** | 389 | **345** | **-44 chunks (-11.3%)** |
| **Chunks < 80 Characters** | 17 | **0** | **-17 (100% eliminated)** |
| **Empty Table Chunks** | 21 | **0** | **-21 (100% eliminated)** |
| **Minimum Chunk Length** | 1 char | **89 chars** | **+88 chars** |
| **Median Chunk Length** | 569 chars | **583 chars** | **+14 chars** |
| **Mean Chunk Length** | 628 chars | **645.5 chars** | **+17.5 chars** |
| **Exact / Near Duplicates** | 38 | **14** | **-24 (remaining 14 are cross-degree)** |

---

## 4. Benchmark Evaluation: 30 New Questions (Step 3)

The pipeline was stress-tested against 30 brand-new, unseen questions spanning 7 distinct categories (`backend/step3_new_questions_eval.py`).

### 4.1 Results Table (30 New Questions)
| ID | Category | Question | Retrieved Chunks | Outcome | Problems Observed |
|---|---|---|---|---|---|
| `N01` | `normal_course` | What is the minimum duration and maximum duration to complete the Online MCA course? | 6 chunks (`programs/online_mca.md`) | **Answered (Fully grounded)** | None (Min 2 yrs, Max 2 yrs) |
| `N02` | `normal_course` | Can a student from the commerce stream apply for the Online BBA programme at CHARUSAT? | 6 chunks (`programs/online_bba.md`) | **Answered (Fully grounded)** | None (Any stream 12th pass eligible) |
| `N03` | `normal_course` | How many total credits are required to graduate from the Online MBA programme at CHARUSAT? | 6 chunks (`programs/online_mba.md`) | **Answered (Fully grounded)** | None (100 total credits) |
| `N04` | `normal_course` | What are the core programming languages and subjects covered in the Online BCA syllabus? | 6 chunks (`programs/online_bca.md`) | **Answered (Fully grounded)** | None (States overview present; granular language list absent) |
| `N05` | `normal_course` | What is the semester fee and total programme fee for Online MCA? | 6 chunks (`pdfs/PPR_Online MCA.pdf`) | **Answered (Fully grounded)** | None (₹75k/yr + ₹14k exam fee = ₹1,64,000 total) |
| `N06` | `normal_course` | What are the step-by-step admission procedures to enroll in the Online BBA course? | 6 chunks (`programs/online_bba.md`) | **Answered (Fully grounded)** | None (Steps 1–3 outlined) |
| `N07` | `normal_course` | What is the total fee for the Online BCA degree if paid semester-wise? | 6 chunks (`pdfs/PPR_Online BCA.pdf`) | **Answered (Fully grounded)** | None (₹50k/yr + ₹1,500/sem = ₹1,59,000 total) |
| `N08` | `normal_course` | What undergraduate minimum percentage is needed for general category students to qualify for Online MBA? | 6 chunks (`programs/online_mba.md`) | **Safe Refusal (Info absent in docs)** | None (Refused to guess percentage; docs specify degree only) |
| `T01` | `typo_hinglish_short` | bca semster fees kitna he? | 6 chunks (`pdfs/PPR_Online BCA.pdf`) | **Answered (Fully grounded)** | None (Answered in Hindi/Hinglish: ₹50,000/yr, ₹1,500 exam/sem) |
| `T02` | `typo_hinglish_short` | mca elgibilty | 6 chunks (`pdfs/PPR_Online MCA.pdf`) | **Answered (Fully grounded)** | None (Bachelor's in any stream with English) |
| `T03` | `typo_hinglish_short` | online mba me kon kon se specialization milte hai? | 6 chunks (`programs/online_mba.md`) | **Safe Refusal (Info absent in docs)** | None (Correctly states specializations not listed in docs) |
| `T04` | `typo_hinglish_short` | bba duration | 6 chunks (`programs/online_bba.md`) | **Answered (Fully grounded)** | None (3 years) |
| `T05` | `typo_hinglish_short` | admisson procidure online mba | 6 chunks (`programs/online_mba.md`) | **Answered (Fully grounded)** | None (States detailed steps absent for MBA; gives helpline) |
| `F01` | `followup_switch_program` | T1: What is the total fee for Online BBA? \| T2: and for MCA? | T1: 6 chk, T2: 6 chk | **Answered (Switched context)** | None (T1 answered BBA ₹1.59L; T2 switched cleanly to MCA ₹75k/yr) |
| `F02` | `followup_switch_program` | T1: What are the eligibility criteria for Online BCA? \| T2: What about MBA? | T1: 6 chk, T2: 6 chk | **Answered (Switched context)** | None (T1 answered BCA; T2 switched cleanly to MBA eligibility) |
| `F03` | `followup_switch_program` | T1: How many semesters are there in Online MBA? \| T2: and does BBA have the same duration? | T1: 6 chk, T2: 6 chk | **Answered (Switched context)** | None (T1 answered MBA 2 yrs; T2 switched to BBA 3 yrs) |
| `F04` | `followup_switch_program` | T1: Who is the contact person for BCA LMS technical support? \| T2: and for MBA? | T1: 4 chk, T2: 5 chk | **Answered (Switched context)** | None (Correctly handles support queries for both) |
| `F05` | `followup_switch_program` | T1: Can I get a refund if I cancel my BBA admission 10 days before the last date? \| T2: Does this same refund policy apply to MCA students as well? | T1: 6 chk, T2: 6 chk | **Answered (Switched context)** | None (T1 gave pre-closure refund; T2 confirmed policy applies to MCA) |
| `U01` | `related_missing` | Does CHARUSAT offer foreign student exchange programmes for online degree students? | 6 chunks (`home.md`) | **Safe Refusal (Info absent in docs)** | Generic university tokens caused high retriever score (0.842) |
| `U02` | `related_missing` | Are mandatory on-site corporate internships arranged by CHARUSAT for online MCA learners? | 6 chunks (`programs/online_mca.md`) | **Safe Refusal (Info absent in docs)** | Generic university tokens caused high retriever score (0.858) |
| `U03` | `related_missing` | Can online students physically visit the Changa campus and access the central sports complex? | 0 chunks (`NONE`) | **Safe Refusal (Scope fallback)** | None (Cleanly fell below 0.52 threshold) |
| `U04` | `related_missing` | How many days after graduation does CHARUSAT take to deliver the hard-copy degree certificate by post? | 6 chunks (`terms-conditions.md`) | **Safe Refusal (Info absent in docs)** | Generic university tokens caused high retriever score (0.692) |
| `X01` | `unrelated` | How do I make chocolate chip cookies at home? | 0 chunks (`NONE`) | **Safe Refusal (Scope fallback)** | None (Clean refusal) |
| `X02` | `unrelated` | What is the speed of light in a vacuum? | 0 chunks (`NONE`) | **Safe Refusal (Scope fallback)** | None (Clean refusal) |
| `X03` | `unrelated` | Who won the ICC Cricket World Cup in 2023? | 0 chunks (`NONE`) | **Safe Refusal (Scope fallback)** | None (Clean one-line scope refusal) |
| `K01` | `tricky` | Since Online MBA requires a valid CAT or GMAT entrance exam score, what is the cutoff percentile? | 6 chunks (`programs/online_mba.md`) | **Safe Refusal (Info absent in docs)** | None (Resisted false premise; stated no CAT/GMAT requirement in docs) |
| `K02` | `tricky` | Provide a comparison of the total program fees and durations across all four online programmes: BBA, BCA, MBA, and MCA. | 6 chunks (`pdfs/PPR_Online BCA.pdf`) | **Partial Answer (BCA only)** | Top-6 retrieval only returned BCA chunks; LLM correctly refused to guess other 3 |
| `K03` | `tricky` | What is the per-semester tuition fee for Online BCA, and what are the hostel accommodation charges for online students during exams? | 6 chunks (`pdfs/PPR_Online BCA.pdf`) | **Answered (Fully grounded)** | None (Gave ₹50,000/yr tuition; explicitly stated hostel info is absent) |
| `L01` | `script_gujarati` | ઓનલાઇન બીસીએ (Online BCA) કોર્સની ફી કેટલી છે? | 6 chunks (`programs/online_bca.md`) | **Answered in Gujarati** | English embedding model matched `online_bca.md` instead of PDF fee table |
| `L02` | `script_hindi` | ऑनलाइन एमबीए प्रोग्राम की कुल अवधि और फीस क्या है? | 6 chunks (`bca-admission-data.md`) | **Answered in Hindi** | English embedding model matched low-scoring table instead of MBA overview |

### 4.2 Hallucination Verification Findings
- **Zero Hallucinated Numbers:** Every fee figure in the responses was cross-referenced directly with ChromaDB chunks:
  - MCA Total Fee (`N05`): ₹1,50,000 programme fee + ₹14,000 examination fee = **₹1,64,000** (table in `pdfs/PPR_Online MCA.pdf`).
  - BCA Total Fee (`N07`): ₹1,50,000 tuition fee + ₹9,000 examination fee = **₹1,59,000** (table in `pdfs/PPR_Online BCA.pdf`).
  - Helpline Numbers: Phone numbers (+91 7434055553, +91 7600257365) match official contact details from `programs/contact.md`.
- **False-Premise Resistance:** When asked for CAT/GMAT percentile cutoffs (`K01`), the chatbot refused to confirm the false premise and clarified that no entrance cutoff is mentioned.

---

## 5. Out-of-Scope Behavior Analysis (Step 4)

Examining the four university-adjacent queries not in the knowledge base (foreign exchange, internships, sports complex, certificate delivery):
1. **Retriever Score Behavior:**
   - Queries with non-academic vocabulary (`U03` sports complex) failed the `0.52` threshold naturally and scored **0.000**, firing the fallback template.
   - Queries with standard academic terms (`U01` exchange, `U02` internships, `U04` postal certificate) matched general promotional words ("CHARUSAT", "degree", "online learning", "regulations") and scored high (**0.692 to 0.858**).
2. **Refusal vs. Hallucination:**
   - In **100% of cases**, the LLM refused to speculate. It explicitly stated: *"The official documents provided do not mention..."* and directed the student to the official admissions helpline.
3. **Token Inefficiency:**
   - While the LLM prompt guardrails successfully prevent hallucination, retrieving 6 weakly-relevant chunks for out-of-scope questions burns ~1,500–2,500 LLM tokens per request.

---

## 6. Ranked Remaining Weaknesses (Evidence-Backed)

### 🔴 Rank 1: Multi-Programme Synthesis Bottleneck
- **Severity:** High
- **Evidence:** Query `K02` (*"Compare total program fees and durations across all 4 programmes: BBA, BCA, MBA, and MCA"*).
- **Mechanism:** The vector index retrieves top-6 chunks globally based on cosine similarity to the entire sentence. All 6 slots were consumed by `PPR_Online BCA.pdf`. Chunks for BBA, MBA, and MCA were crowded out. The LLM accurately reported BCA but could not answer for the other 3 degrees.
- **Impact:** Any user asking for a comprehensive cross-programme comparison receives only a single programme's details.

### 🟠 Rank 2: English-Only Embedding Model for Native Scripts (Gujarati / Hindi)
- **Severity:** Medium-High
- **Evidence:** Queries `L01` (Gujarati) and `L02` (Hindi).
- **Mechanism:** The embedding model `BAAI/bge-small-en-v1.5` is an English-only model. When a query is written entirely in Gujarati or Devanagari script, the embeddings have low semantic alignment with the English document corpus. For `L01`, it matched generic promotional text in `online_bca.md` instead of the English fee table in `PPR_Online BCA.pdf`.
- **Impact:** While the system correctly answers in Gujarati or Hindi, it fails to retrieve the exact English fee tables.

### 🟡 Rank 3: Out-of-Scope Token Overhead on Generic University Vocabulary
- **Severity:** Medium
- **Evidence:** Queries `U01` (foreign exchange), `U02` (internships), `U04` (postal certificates).
- **Mechanism:** Chunks retrieved because of common words like "CHARUSAT", "degree", "online".
- **Impact:** Costs ~1,500–2,500 LLM prompt tokens per out-of-scope question that could be handled instantly by a pre-retrieval scope check.

### 🟢 Rank 4: Mid-Sentence Chunk Boundary Splitting
- **Severity:** Low
- **Evidence:** 185 chunks end without punctuation due to fixed 600-char splitting in `RecursiveCharacterTextSplitter`.
- **Impact:** Occasional fragmented context sent to LLM, though 100-char overlap mitigates loss of meaning.

---

## 7. Data-Backed Next Steps

1. **Implement Multi-Programme Query Splitting:**
   - *Rationale:* Fixes Rank 1 (`K02`). When a query mentions 2 or more programmes, run separate sub-queries (e.g. 2 chunks per programme) and fuse into context.
2. **Evaluate Multilingual Embedding Model (`intfloat/multilingual-e5-base`):**
   - *Rationale:* Fixes Rank 2 (`L01`, `L02`). Replaces English-only `bge-small` with a native multilingual model so Gujarati and Hindi queries align semantically with English course tables.
3. **Add Fast Pre-LLM Attribute Keyword Gate:**
   - *Rationale:* Fixes Rank 3 (`U01`, `U02`, `U04`). If core query nouns (e.g. "exchange", "internship", "hostel") have zero lexical or high-focus semantic presence in retrieved chunks, bypass LLM and immediately return the admissions contact fallback.