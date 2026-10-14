# ROUND 5 — Engineering Report

**Date:** 2026-10-14  
**Completed steps:** 0a (backup), 1, 4, 5, 6, 7, 8  
**Deferred:** 0b (live audit), 2 (topic lexicon JSON), 3 (cross-programme fallback), 9 (final test run)

---

## 1. Answer Classification — Before / After (Static Analysis)

| Classification | Before Round 5 | After Round 5 |
|---------------|---------------|--------------|
| SAME_AS_ANOTHER_QUESTION | ~15 (all fee/admission follow-ups in a session) | 0 (each gets unique standalone_q) |
| WRONG_CONTENT (off-topic false positive) | ~8 (score, match, function, cook, etc.) | 0 (guarded by course keyword check) |
| WRONG_CONTENT (greeting typo) | ~3 (hii, heyy, helloo) | 0 |
| WRONG_CONTENT (refund regex miss) | ~2 ("refundable", "refunded") | 0 |
| WRONG_CONTENT (contact tag stripped) | ~4 | 0 |
| WRONG_DATA_EXISTS (BCA/MCA docs Q after BBA) | ~2 | PARTIAL_OK (cross-prog deferred) |
| WRONG_DATA_EXISTS (missing fee cells shown as "–") | ~3 | 0 (prompt rule: "not in documents") |
| WRONG_DATA_EXISTS (eval% conflict unreported) | ~1 | 0 (prompt flags both sources) |
| CORRECT / CORRECT_REFUSAL | ~40 | ~55+ |

*Numbers are estimates from static code inspection; exact counts require live run.*

---

## 2. Changes Per Step

### Step 1 — `conversation.py`

**Function:** `_build_standalone_question()`, `_COMPARE_RE`

| Before | After |
|--------|-------|
| Follow-ups replaced by topic template: "fee structure and payment details" | User words kept; only missing context (programme, year) appended in `(...)` |
| Cache key collisions: all fee follow-ups got same key | Each question text is unique → distinct cache entries |
| `_COMPARE_RE` missed "each program", "all four", "both programs" | Extended with all variants |
| Refund regex `\b(refund)\b` missed "refundable" | Fixed to `refund\w*` |

**Files changed:** `backend/app/conversation.py`

### Step 4 — `prompt.py`

**Added rules:**
- Never write "–" or "-" for missing numeric values; write "not in documents"
- Never present a total unless every component is in the retrieved context
- For evaluation% conflicts: state both values with source

**Files changed:** `backend/app/prompt.py`

### Step 5 — `contacts.py`

| Before | After |
|--------|-------|
| `(BCA/MCA)` tag stripped from displayed name | Tag kept: "Mr. Sanket Patel (BCA/MCA) (8460549025)" |
| Course Mentor / Student Services unreachable (wrong topic strings) | Mapped directly via t_lower keyword check |
| LMS/Exam filtered before Accounts/Admissions in keyword priority | LMS checked before Examinations; Admissions is final fallback |

**Files changed:** `backend/app/contacts.py`

### Step 6 — `smalltalk.py`

| Before | After |
|--------|-------|
| `_GREETING_RE` used strict `\b` → "hii", "heyy" not matched | Regex tolerates repeated letters: `h+i+h*`, `h+e+y+`, `h+e+l+o+` |
| `_OFFTOPIC_RE.search()` on whole message → false positives | Guarded: runs only when `_COURSE_KEYWORD_RE` has no match |
| `_RUDE_RE.search()` same issue | Same guard applied |
| `_NON_ENGLISH_RE` contained Hindi/Gujarati words/Unicode ranges | Removed; pure non-ASCII detection only |

**Files changed:** `backend/app/smalltalk.py`

### Step 7 — `rag_chain.py`

| Before | After |
|--------|-------|
| `self.last_status`, `self.last_conflicts`, `self.last_timing` written on shared object | Local variables `_status`, `_conflicts`, `_timing` per call |
| Two concurrent requests mix metadata | Each request has its own local state; shared attrs kept only for single-threaded diagnostics |
| Added `AnswerResult` dataclass | Future callers can use structured return instead of attribute reads |

**Files changed:** `backend/app/rag_chain.py`

---

## 3. Remaining Problems

| Problem | Severity | Deferred Step |
|---------|----------|---------------|
| Cross-programme fallback when inherited programme has no answer | Medium | Step 3 |
| Topic lexicon still in code (not in topic_lexicon.json) | Low | Step 2 |
| BCA/MCA FAQ question text missing from chunks (scraper issue) | Medium | Step 8c (report only) |
| Documents Q after BBA session: BCA/MCA docs not searched | Medium | Step 3 |
| Fee table chunk may not always be in top-6 for complex fee questions | Low | (fee_candidate_search exists; may need threshold tuning) |
| Untitled-1.txt in pdfs/ not ingested | Low | Step 8 (decision needed by user) |
| No topic_lexicon.json yet (R1 requirement) | Low | Step 2 |

---

## 4. Decisions Needed

1. **`Untitled-1.txt` in `knowledge_base/pdfs/`:** Delete it, or ingest it as a structured fee data source?
2. **Cross-programme fallback (Step 3):** Should "documents required" always search BCA and MCA when no programme is in context, or only when inherited programme yields NOT_FOUND?
3. **Topic lexicon JSON (Step 2):** Schedule for Round 6? Would also enable admin editing of keywords without code changes.
4. **BCA/MCA FAQ questions lost (scraper):** Re-scrape with a fix? Or manually add Q+A pairs to `online_bca.md` / `online_mca.md`?
5. **BBA/MBA mandatory documents:** Add to `online_bba.md` and `online_mba.md` after verifying with admissions team?

---

## 5. R1 Compliance Check

No amounts, phone numbers, test questions, or programme facts were added to code or prompts. The prompt only contains structural rules (how to handle data from documents). Phone numbers live only in `contact.md` (KB file, not code). Keyword lists remain in `_TOPIC_REGEXES` in `conversation.py` (pending migration to JSON in Step 2).
