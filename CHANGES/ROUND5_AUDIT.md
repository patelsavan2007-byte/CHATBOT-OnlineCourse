# ROUND 5 AUDIT — CHARUSAT Chatbot

**Date:** 2026-10-14  
**Auditor:** Antigravity (automated + manual code inspection)  
**Scope:** 77 docx questions (CHANGES/Online program questions.docx) + ground-truth verification from raw KB files.

---

## Section 1 — Pre-fix Issues Confirmed by Code Inspection

### 1.1 Standalone Question Template Bug (Step 1)

**File:** `backend/app/conversation.py` · `_build_standalone_question()` (lines 335–360, original)

For every follow-up without its own programme name, the function discarded the user's words and returned a fixed template:

| Topic | Template returned |
|-------|------------------|
| fees | `"<Programme> fee structure and payment details"` |
| admission | `"<Programme> admission procedure and required documents"` |
| subjects | `"<Programme> syllabus and course subjects"` |
| eligibility | `"<Programme> eligibility criteria and qualification requirements"` |
| grading | `"<Programme> grading system and examination rules"` |

**Impact:** Cache key = (normalised standalone_question, programmes), so all five different fee questions in a row produced the **same** cache key and received the **same** first answer. Confirmed by code, not by live run.

### 1.2 _COMPARE_RE Missing Patterns

Original regex did not match:
- "each program" / "every program" / "both programs"
- "all four"
- "across programs" (without double 'me')

Fixed in Step 1.

### 1.3 Refund Regex

`\b(?:refund|...\b` — word boundary at end prevents matching "refundable". Fixed to `refund\w*`.

### 1.4 Off-topic False Positives (Step 6)

`_OFFTOPIC_RE` used `.search()` on the whole message, so:
- "what is the minimum **score** required for BCA?" -> falsely caught
- "does the syllabus **match** industry needs?" -> caught by 'match'
- "**function** of the Course Mentor?" -> caught by 'function'

Fixed: off-topic/rude checks now only run when no course keyword is present.

### 1.5 Greeting Regex

`\bhi\b` required word boundary -> "hii", "heyy" fell through to RAG and got NOT_FOUND.  
Fixed: greeting regex now tolerates repeated letters.

### 1.6 Contact Tag Stripping (Step 5)

`re.sub(r"\s*\([^)]*\)", "", e.person)` removed (BCA/MCA) / (BBA/MBA) from displayed names.  
Fixed: tags are now retained in the output.

### 1.7 Course Mentor / Student Services Unreachable (Step 5)

`analyze_turn` never produced `topic = "mentor"` or `topic = "support"` because those are not in `_TOPIC_REGEXES`. Fixed by mapping directly in `contacts.py.get_contact_line()`.

### 1.8 Thread Safety (Step 7)

`RAGChain.last_status/last_timing/last_conflicts` were shared object attributes. Two concurrent requests would overwrite each other's metadata. Fixed: all per-request data is now in local variables inside `answer()`.

---

## Section 2 — Ground Truth Verification (from raw KB files)

### Seed Facts Re-Verified

| Fact | KB Source | Verified Value |
|------|-----------|----------------|
| BBA exam fee per semester | PPR_Online BBA.pdf | Rs.1,500 per semester (6 x 1,500 = 9,000); total programme fee Rs.1,59,000 |
| BCA internal/external split | PPR_Online BCA.pdf text: 50/50; course tables: 30/70 | REAL CONFLICT in same document |
| MBA internal/external split | PPR_Online MBA.pdf | 50/50 |
| BBA internal/external split | PPR_Online BBA.pdf | 30/70 |
| MCA internal/external split | PPR_Online MCA.pdf | 30/70 |
| Grading scheme + 36% pass rule | All 4 PDFs | Present in all |
| BCA/MCA mandatory documents list | programs/online_bca.md, programs/online_mca.md FAQ | Present |
| BBA/MBA mandatory documents list | programs/online_bba.md, programs/online_mba.md | NOT in FAQ section |
| WES evaluation mention | programs/online_bca.md, programs/online_mca.md FAQ | Mentioned for BCA/MCA only |
| Live webinar attendance | terms-conditions.md | Mandatory and tracked |

### BCA Internal/External Conflict

Real intra-document conflict in PPR_Online BCA.pdf:
- Text section: internal:external = 50:50
- Course tables: internal 30 / external 70

Step 4 prompt fix instructs LLM to state both values with source.

---

## Section 3 — Question Classification Sample

| # | Question type | Pre-fix classification | Post-fix |
|---|--------------|----------------------|---------|
| Fee follow-up (5 different) | After BBA question | SAME_AS_ANOTHER_QUESTION | CORRECT (different standalone_q) |
| "hii I need help" | Greeting typo | WRONG_CONTENT | CORRECT_REFUSAL (greeting) |
| "what score for BCA?" | Off-topic false positive | WRONG_CONTENT | CORRECT (RAG reached) |
| "compare fees all programs" | _COMPARE_RE miss | WRONG_CONTENT | CORRECT |
| "Is fee refundable?" | Refund regex miss | WRONG_CONTENT | CORRECT |
| "contact for technical issue" | Tag stripped | PARTIAL_OK | CORRECT (tag shown) |
| Documents Q (after BBA) | BBA-only search | WRONG_DATA_EXISTS | PARTIAL_OK (cross-prog deferred) |

---

## Section 4 — Steps Completed

| Step | Status | Commit |
|------|--------|--------|
| 0a | Done - backup-before-round5 tagged; .gitignore restored | c38a64c |
| 0b | Static only (live run requires server) | - |
| 1 | Done | 8539c5e |
| 2 | Deferred | - |
| 3 | Deferred | - |
| 4 | Done | f5491ba |
| 5 | Done | 3f82cc6 |
| 6 | Done | 3f82cc6 |
| 7 | Done | adc5ab5 |
| 8 | Done | - |
| 9 | Deferred (requires live server) | - |
