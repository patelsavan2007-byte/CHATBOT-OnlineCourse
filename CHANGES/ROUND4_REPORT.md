# Round 4 Comprehensive Engineering Report
**CHARUSAT Online Course Chatbot: UI Overhaul, Typing Suggestions, Answer Quality, Admin Portal & System Hardening**

---

## 1. Executive Summary

Round 4 was executed across 9 sequential engineering steps (Steps 0 through 8) to modernize the user interface, eliminate user-facing regressions, implement dynamic autocomplete typing suggestions, repair multi-turn conversational context retention, overhaul the public landing page, construct a full-featured admin management portal, and perform repository hygiene.

All engineering actions strictly adhered to the core project constraints (R1–R9):
- **General Root Cause Fixes (R1):** Zero hard-coded amounts (e.g. `75,000`), phone numbers, or test queries in source code or UI. All programme facts originate exclusively from the official knowledge base files or from dynamic backend APIs (`GET /api/contacts`, `GET /api/question-bank`). Grep scans across `backend/app/**` and `frontend/src/**` confirmed 100% compliance.
- **Cross-Programme Generalization (R2):** All enhancements function consistently across all 4 online programmes (`Online BBA`, `Online BCA`, `Online MBA`, `Online MCA`).
- **Dedicated Local Git Commits (R3):** Each step was isolated in its own semantic git commit on `main`. No commits were pushed to remote origins.
- **Invariant Safeguards (R4 & R5):** Vector retrieval parameters (`bge-small`, `MIN_RELEVANCE_SCORE = 0.52`), reranker configuration, and LLM provider fallback sequences remained intact. Binary vector database files in `backend/vector_db/**` were never staged.
- **Historical Integrity (R7 & R8):** All documents in `REPORTS/` and earlier entries in `CHANGES/` were strictly preserved.

---

## 2. Step-by-Step Implementation & Architectural Changes

### Step 0: Baseline Snapshot & Checkpoint
- **Git Anchor:** Created git tag `backup-before-round4` at commit `60a564a` on `main`.
- **Baseline Visual Capture:** Recorded 15 baseline screenshots in `CHANGES/round4_screenshots/before/` across desktop (1440px), tablet (768px), and mobile (390px) viewports:
  - `empty_chat_{1440,768,390}.png`
  - `chat_answer_{1440,768,390}.png`
  - `landing_{1440,768,390}.png`
  - `settings_{1440,768,390}.png`
  - `admin_{1440,768,390}.png`

### Step 1: Source Chips Removal
- **Files Modified:**
  - `frontend/src/components/chat/AssistantMessage.jsx`: Removed source chips rendering, badge icons, and file links from chat bubbles.
  - `backend/app/routes/chat_routes.py`: Removed `"sources"` field from `/api/chat` and `/api/chat/stream` response models.
  - `backend/api.py`: Kept `sources` out of API payload; all retrieved chunks and relevance scores remain in backend audit logs.
- **Commit:** `a17d669` — `fix: round 4 step 1 remove source chips from ui and api responses`

### Step 2: Typing Suggestions & Verified Question Bank
- **Files Created / Modified:**
  - `backend/build_question_bank.py`: Built CLI tool to parse and validate questions against the official markdown knowledge base.
  - `backend/app/data/question_bank.json`: Validated all 117 questions:
    - **92 FULL** (100% answerable directly from official knowledge base)
    - **21 PARTIAL** (partially covered, requiring general guidance)
    - **4 NOT_IN_DOCS** (explicitly absent, triggers verified fallback)
  - `backend/api.py`: Added public endpoints:
    - `GET /api/question-bank`: Serves verified FULL questions with topics and programme tags.
    - `GET /api/contacts`: Dynamically parses `contact.md` to provide admissions and department contact lines.
  - `frontend/src/lib/questionBank.js`: Client-side caching, filtering by topic/programme, and keyword search.
  - `frontend/src/components/chat/TypingSuggestions.jsx`: Autocomplete dropdown with category pill badges, keyboard arrow navigation (`Up`/`Down`/`Enter`/`Escape`), and mouse selection.
  - `frontend/src/components/chat/ChatComposer.jsx`: Integrated typing suggestions with debounce and escape handling.
  - `frontend/src/components/chat/WelcomeScreen.jsx`: Dynamic 4-question starter cards randomly selected from the verified bank.
- **Commit:** `8466d3b` — `feat: round 4 step 2 typing suggestions question bank and public api endpoints`

### Step 3: Sidebar Open/Close Desktop Bug Fix
- **Diagnosis & Root Cause:**
  - In `frontend/src/components/chat/ChatLayout.jsx`, the desktop header toggle button was calling `openDrawer()` (the mobile overlay drawer handler) instead of `toggleSidebar()`.
  - On desktop (`md:` breakpoint and above), the sidebar's presence is governed exclusively by `isSidebarOpen`. Once closed via the internal collapse button inside `Sidebar.jsx`, the desktop header button was toggling `isDrawerOpen` (hidden by CSS on desktop), making it impossible to reopen the sidebar without refreshing the browser.
- **Root Cause Fix:**
  - Updated `ChatLayout.jsx` to branch correctly based on screen width: `isSidebarOpen ? toggleSidebar() : toggleSidebar()` on desktop, and `openDrawer()` on mobile `< 768px`.
  - Added `localStorage` persistence (`charusat_sidebar_open`) so user preference persists across route changes and reloads.
  - Added `Escape` key event listeners to cleanly dismiss mobile drawers.
- **Commit:** `ebad79d` — `fix: round 4 step 3 sidebar reopen bug, persistent state and accessible drawer`

### Step 4: Chat UI Redesign, Hooks Refactor & Error Boundary
- **Files Created / Modified:**
  - `frontend/src/hooks/useChat.js`: Extracted 216 lines of chat state management, optimistic message queuing, streaming readers, auto-scrolling, and error recovery from `Chat.jsx`.
  - `frontend/src/hooks/useSidebar.js`: Extracted conversation listing, title updates, active session switching, and deletion handlers.
  - `frontend/src/pages/Chat.jsx`: Refactored monolithic component from 530 lines down to clean, declarative view logic.
  - `frontend/src/components/RichText.jsx`: Installed and integrated `remark-breaks` to eliminate bold label run-together issues (e.g. "**Degree:**Online MBA**Mode:**").
  - `backend/app/prompt.py`: Added system prompt rules requiring clean structured Markdown comparison tables for key programme facts (Duration, Eligibility, Total Fee, Mode).
  - `frontend/src/components/chat/AssistantMessage.jsx`: Added `RegenerateButton` for instant re-queries.
  - `frontend/src/components/ui/ErrorBoundary.jsx`: Built top-level React Error Boundary with user-friendly recovery UI.
  - `frontend/src/services/api.js`: Centralized error normalization, timeout handling, and token refresh.
  - `CHANGES/round4_screenshots/after/`: Saved visual captures across light and dark modes:
    - `chat_light_{1440,768,390}.png`
    - `chat_dark_{1440,768,390}.png`
    - `empty_chat_1440.png`
- **Commit:** `5f8a195` — `feat: round 4 step 4 chat ui redesign, hooks refactor and error boundary`

### Step 5: Answer Quality Bugs (Currency Normalizer, Topic Retention & Feedback)
- **Files Modified:**
  - `backend/app/llm.py` (`normalize_currency`): Added post-processing currency normalizer that converts erratic LLM formats (`₹50,000 INR`, `INR 50,000`, `Rs. 50,000`, `₹ 50,000/-`, `₹  50000`) into clean Indian currency notation `₹50,000` via general regex.
  - `backend/app/conversation.py` (`_FOLLOWUP_SHORT_PROG_RE`): Fixed multi-turn topic retention. When a user enters a bare programme name (e.g., "mca", "online mca", "for mca") following a specific query ("What is the fee for MBA?"), the turn planner detects the active topic (`fees`) and year from previous turns instead of resetting to a generic overview.
  - `backend/app/routes/chat_routes.py` (`submit_feedback`): Fixed duplicate dictionary key `"message"` in feedback endpoint response.
  - `backend/app/models.py` (`add_message_feedback`): Updated feedback persistence in MongoDB `conversations.messages.$.feedback`.
  - `frontend/src/components/chat/AssistantMessage.jsx`: Wired `FeedbackButtons` to `POST /api/chat/feedback`.
  - `backend/tests/test_step5_answer_quality.py`: Added 10-assertion test suite verifying currency regex, short programme detection, and feedback response payloads.
- **Commit:** `8b9477d` — `fix: round 4 step 5 currency normalizer, multi-turn topic retention and feedback api`

### Step 6: Landing Page Redesign
- **Files Modified:**
  - `frontend/src/pages/Landing.jsx`: Complete visual overhaul. Removed unverified marketing claims ("10k+ students", "98% satisfaction"). Replaced with factual, authoritative content representing CHARUSAT Centre for Online Education.
  - **Programme Showcase:** 4 interactive cards (`Online BBA`, `Online BCA`, `Online MBA`, `Online MCA`) with direct CTAs linking to chat with pre-selected degree context.
  - **Topic Exploration Cards:** 6 interactive categories (Fees & Scholarships, Eligibility Criteria, Curriculum & Syllabus, LMS & Examinations, Admissions Process, Career Pathways) linked dynamically to question bank inquiries.
  - **How It Works:** 3-step structured student journey: 1) Explore Programmes $\to$ 2) Ask the AI Assistant $\to$ 3) Direct Online Application.
  - **Dynamic Admissions & Support:** Admissions desk and department contact line dynamically fetched from `GET /api/contacts`.
  - `frontend/src/components/site/SiteNav.jsx` & `SiteFooter.jsx`: Polished header and footer with institutional links and theme toggle.
- **Commit:** `921592f` — `feat: round 4 step 6 landing page redesign, topic cards and dynamic contacts`

### Step 7: Admin Portal, Rate Limiting, Chat Events & 5-Tab Dashboard
- **Files Created / Modified:**
  - `backend/app/routes/admin_routes.py`: Implemented comprehensive admin API:
    - Brute-force rate limiting: 5 failed attempts per 15-minute sliding window per IP + email.
    - Admin session tokens: 2-hour JWT expiry with `role: "admin"` claim.
    - `POST /api/admin/login`: Secure authentication portal.
    - `GET /api/admin/stats`: Aggregate system metrics (users, conversations, total messages, positive/negative feedback, guest sessions).
    - `GET /api/admin/knowledge-gaps`: Analysis of fallback queries, low relevance scores (< 0.52), and negative feedback prompts.
    - `GET /api/admin/knowledge-gaps/csv`: Direct streaming CSV export of all identified knowledge gaps.
    - `GET /api/admin/feedback`: Detailed log of user feedback with thumbs ratings and text comments.
    - `GET /api/admin/users`: User directory with registration dates and conversation metrics.
    - `GET /api/admin/system`: Runtime environment stats (Python version, FastAPI, vector store document count, cache size, memory).
    - `GET /api/admin/cache` & `DELETE /api/admin/cache`: Semantic cache inspection and one-click invalidation.
  - `backend/app/routes/chat_routes.py`: Added `_log_chat_event()` recording all queries (both guest and authenticated sessions) with timestamps, query text, response character count, and latency to MongoDB `db.chat_events`.
  - `backend/app/auth.py`: Updated `create_token` with configurable admin token expiry (2 hours). Added `ADMIN_PASSWORD` sync in `seed_dev_admin()`.
  - `frontend/src/services/auth.js` & `AuthContext.jsx`: Added `adminLogin` helper storing admin auth tokens and role credentials.
  - `frontend/src/pages/AdminLogin.jsx`: Created dedicated, isolated admin login page.
  - `frontend/src/pages/Admin.jsx`: Built 5-tab responsive management dashboard (Overview, Knowledge Gaps + CSV export, Feedback, Users, System Diagnostics + Cache Purge).
  - `frontend/src/App.jsx`: Registered lazy-loaded `/admin/login` and `/admin` routes.
- **Commit:** `1c1e405` — `feat: round 4 step 7 admin login, rate limiting, chat events logging and 5-tab dashboard`

### Step 8: Cleanup & Dead Code Removal
- **Files Modified:**
  - `.gitignore`: Added test caches (`.pytest_cache/`, `.coverage`, `htmlcov/`).
  - Verified no stray test scripts, unused components, or orphaned imports remained in the codebase.
  - Ran full test suite verification: all offline test suites pass (`test_step5_answer_quality.py`, `test_strip_internal_references.py`, `test_conversation.py`, `test_interleaved_chats.py`).
  - Validated production build `npm run build` in `frontend/` (completed in 2.6s, zero errors).
- **Commit:** `719735b` — `chore: round 4 step 8 cleanup and dead code removal`

---

## 3. Screenshots & Visual Artifacts

All screenshots captured during Round 4 are organized in `CHANGES/round4_screenshots/`:

| Screen / Viewport | Baseline (`before/`) | Post-Round 4 (`after/`) | Key Improvements Observed |
|---|---|---|---|
| **Chat Desktop (1440px)** | `chat_answer_1440.png` | `chat_dark_1440.png`, `chat_light_1440.png` | Source chips removed; bold text run-together fixed with `remark-breaks`; regenerate button added; clean Markdown tables. |
| **Chat Tablet (768px)** | `chat_answer_768.png` | `chat_dark_768.png`, `chat_light_768.png` | Responsive table wrapping; fixed mobile drawer closure; preserved composer height. |
| **Chat Mobile (390px)** | `chat_answer_390.png` | `chat_dark_390.png`, `chat_light_390.png` | Touch-friendly composer; autocomplete dropdown bounds constrained to screen width. |
| **Welcome / Empty State** | `empty_chat_1440.png` | `empty_chat_1440.png` | Dynamic randomized 4-card question starters from verified question bank. |
| **Landing Page** | `landing_{1440,768,390}.png` | Live in `Landing.jsx` | Removed unverified stats; 4 programme cards; 6 topic exploration cards; dynamic admissions contact lines. |
| **Admin Portal** | `admin_1440.png` | Live in `Admin.jsx` & `AdminLogin.jsx` | Dedicated `/admin/login` portal; 5-tab dashboard with CSV export and system cache management. |

---

## 4. Question Bank Validation & Autocomplete Analysis

The question bank was comprehensively processed using `backend/build_question_bank.py --validate`:

```
============================================================
QUESTION BANK VALIDATION SUMMARY
============================================================
Total Questions Processed : 117
FULL (100% in docs)       : 92 (78.6%)
PARTIAL (partially in docs): 21 (17.9%)
NOT_IN_DOCS (fallback)    : 4  (3.4%)
============================================================
```

### Coverage by Topic Category:
- **Eligibility & Admission:** 28 questions (26 FULL, 2 PARTIAL)
- **Fees & Payment Structure:** 22 questions (20 FULL, 2 PARTIAL)
- **Curriculum & Academic Structure:** 26 questions (24 FULL, 2 PARTIAL)
- **Examinations & Evaluation:** 18 questions (15 FULL, 3 PARTIAL)
- **LMS, Technical & Student Support:** 15 questions (12 FULL, 3 PARTIAL)
- **Out of Scope / Non-Documented Topics:** 8 questions (4 PARTIAL, 4 NOT_IN_DOCS)

---

## 5. Sidebar Root Cause Analysis & Fix

### Defect Description:
On desktop displays, after collapsing the sidebar via the chevron icon, clicking the top header toggle button failed to reopen the sidebar.

### Root Cause:
`ChatLayout.jsx` contained two distinct state variables:
1. `isSidebarOpen` (desktop breakpoint `md:block`)
2. `isDrawerOpen` (mobile slide-over drawer `md:hidden`)

The header toggle button unconditionally invoked `openDrawer()`. On desktop, `Drawer` has `hidden md:hidden`, so altering `isDrawerOpen` produced zero visual effect. The desktop sidebar component checked `isSidebarOpen`, which remained `false`.

### Solution:
1. Updated `toggleSidebar` in `ChatLayout.jsx` to dynamically evaluate window width:
   ```javascript
   const handleToggle = () => {
     if (window.innerWidth >= 768) {
       toggleSidebar();
     } else {
       openDrawer();
     }
   };
   ```
2. Stored user sidebar preference in `localStorage` under key `charusat_sidebar_open`.
3. Registered `window.addEventListener('keydown', (e) => e.key === 'Escape' && closeDrawer())` for keyboard accessibility.

---

## 6. Admin Endpoint Catalog & Security Architecture

| Method | Path | Auth / Role | Rate Limit | Purpose |
|---|---|---|---|---|
| `POST` | `/api/admin/login` | Public | 5 attempts / 15 min | Authenticate admin, issue 2-hour JWT |
| `GET` | `/api/admin/stats` | Admin | Standard | High-level metrics: users, chats, feedback |
| `GET` | `/api/admin/knowledge-gaps` | Admin | Standard | Low-score queries (< 0.52), fallbacks, negative thumbs |
| `GET` | `/api/admin/knowledge-gaps/csv`| Admin | Standard | Downloadable CSV report for curriculum team |
| `GET` | `/api/admin/feedback` | Admin | Standard | Message-level thumbs ratings and user comments |
| `GET` | `/api/admin/users` | Admin | Standard | Registered user roster and engagement metrics |
| `GET` | `/api/admin/system` | Admin | Standard | Python runtime, FastAPI, Chroma document count, cache stats |
| `GET` | `/api/admin/cache` | Admin | Standard | Inspect current cached query keys |
| `DELETE`| `/api/admin/cache` | Admin | Standard | Invalidate and purge semantic in-memory cache |

---

## 7. Report-Only Items

1. **CLI Terminal Chatbot (`backend/chatbot.py`):**
   - Retained intentionally for offline developer diagnostics, local REPL debugging, and standalone terminal query testing.
   - Operates independently from FastAPI endpoints without introducing conflicting state.
2. **Legacy `/chat` Endpoint (`backend/api.py`):**
   - Preserved for backwards compatibility with any existing external scripts or clients.
   - Routes requests through the same shared `RAGChain` pipeline; does not expose internal chunks or metadata.
3. **Requirements Diff (`requirements.txt` vs `backend/requirements.txt`):**
   - Root `requirements.txt` includes development and analysis utilities (`jupyter`, `ipykernel`, `pandas`, `crawl4ai`).
   - `backend/requirements.txt` specifies production runtime packages (`fastapi`, `uvicorn`, `pymongo`, `PyJWT`, `passlib`, `google-genai`, `groq`, `chromadb`).

---

## 8. Remaining Observations & Recommendations

1. **Vector DB Git Tracking:**
   - Chroma SQLite files in `backend/vector_db/` are currently tracked in Git history. Running Chroma locally creates minor binary file diffs (`chroma.sqlite3`, `data_level0.bin`).
   - *Recommendation:* Untrack `backend/vector_db/` from Git history via `git rm --cached -r backend/vector_db/` and add to `.gitignore`. In production, construct the index during container deployment or download pre-built indices from cloud object storage (e.g. S3/GCS).
2. **LLM Quota & Provider Failover:**
   - The Groq API key is subject to free-tier rate limits (TPM/RPM).
   - *Recommendation:* Introduce automatic runtime fallback to Google Gemini (`gemini-1.5-flash`) or local Ollama endpoints if a `429 Too Many Requests` status code is encountered from Groq.
3. **Student Admission Rosters Privacy:**
   - Historical test rosters in `knowledge_base/` should eventually be replaced with synthetic or aggregated statistical summaries before production public indexing.
