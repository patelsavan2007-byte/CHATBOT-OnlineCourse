# Launch Readiness Checklist - CHARUSAT Online Programmes Assistant

Generated: 2026-10-28
Branch: `redesign/chat-first`

Privacy and Terms pages: removed at owner request on 2026-10-30, still required before public launch.

---

## 1. Confirmed vs Unconfirmed Operational Facts

| Item | Current Value in `src/config/site.js` | Source of Truth / Verification Status | Launch Requirement |
|---|---|---|---|
| **Short Product Name** | `CHARUSAT Assistant` | Confirmed from brand specifications | Validated |
| **Full Product Name** | `CHARUSAT Online Programmes Assistant` | Confirmed from academic charter | Validated |
| **Operator Legal Name** | `Charotar University of Science and Technology` | Confirmed official university identity | Validated |
| **Operated by University** | `true` | Confirmed by project lead | Official copyright and disclaimer active |
| **Production Domain** | `CONFIRM` | Unconfirmed pending production DNS linkage | Replace placeholder before DNS flip |
| **Contact Email** | `CONFIRM` | Unconfirmed | Designated helpdesk email required |
| **Grievance Email** | `CONFIRM` | Unconfirmed (India DPDP Act 2023 requirement) | Appoint Grievance Officer email |
| **Data Retention Period** | `CONFIRM` | Unconfirmed | Specify retention window (e.g. "12 months") |
| **Support Phone** | `CONFIRM` | Unconfirmed general helpline | Individual department lines confirmed below |
| **University Portal** | `https://charusat.ac.in` | Confirmed official university URL | Validated |
| **Governing Jurisdiction**| `Gujarat, India` | Confirmed university headquarters | Validated |

### Departmental Contacts (Confirmed from `knowledge_base/contact_directory.md`)
- **Admissions and Fees:** Mr. Darshit Patel (7434055553) / Mr. Kirti Patel (7600257365) - `online-admissions@charusat.ac.in`
- **Student Services:** Mr. Mitesh Patel (9408033391) - `student.services@charusat.ac.in`
- **LMS BCA/MCA:** Mr. Sanket Patel (8460549025) / Mr. Ravi Patel (7574945238) - `lms@charusat.ac.in`
- **LMS BBA/MBA:** Ms. Subhashree S (9688397401) - `lms@charusat.ac.in`
- **Course Academic Mentor:** Dr. Hetal Barad (7434055556) - `course.mentor@charusat.ac.in`
- **Examinations Office:** Mr. Snehal Patel (9409572216) - `exam@charusat.ac.in`

---

## 2. Third-Party Service Inventory & Privacy Policy Disclosure

| Third-Party Service | Purpose | Disclosure status | Data Shared | Notes |
|---|---|---|---|---|
| **Self-Hosted IBM Plex Fonts** | Typography | N/A | None | Self-hosted locally via `@fontsource`. Google Fonts links removed to eliminate third-party visitor IP leakage. |
| **Google Identity Services (GIS)** | Student OAuth Login | Yes (Section 7) | Google OAuth token, Name, Email | Only activated when student selects "Sign in with Google". |
| **Google Gemini API** | Primary LLM for answer generation | Yes (Section 7) | Cleaned user prompt and relevant context chunks | Account credentials and user emails are never sent to Gemini. |
| **Groq API** | Failover LLM for high availability | Yes (Section 7) | Cleaned user prompt and relevant context chunks | Invoked only if Gemini returns 429/503. No user identity passed. |
| **MongoDB Atlas** | Database storage | Yes (Section 8) | Hashed passwords, conversation threads, chat analytics | Encrypted in transit (TLS 1.3) and at rest. IP restricted. |
| **Vercel** | Frontend static edge delivery | Yes (Section 8) | Standard web server requests | SPA rewrites, HSTS, CSP, and immutability headers enforced. |
| **Render** | Backend container hosting | Yes (Section 8) | Application HTTP logs | Free plan container hosting with cold start mitigation. |

---

## 3. Compliance Matrix: 12 Strict Non-Negotiables

| # | Non-Negotiable Rule | Automated Check | Status | Verification Summary |
|---|---|---|---|---|
| 1 | **No purple, violet, indigo; no gradients** | `check:rules` | **PASS** | Design tokens use `#0B5CAD` university blue; zero gradient utilities or hex codes in CSS/JSX. |
| 2 | **No pill shapes; strict radius rules** | `check:rules` | **PASS** | Buttons 6px (`rounded-md`), inputs/cards 8px (`rounded-lg`), composer 12px (`rounded-xl`). Circles strictly limited to status dots, spinners, and avatars with `allow-round`. |
| 3 | **No fake reviews, testimonials, claims** | Manual & Script | **PASS** | All metrics computed live from MongoDB `chat_events`. Zero data displays "No data yet". Ratings < 20 display "Not enough ratings yet". |
| 4 | **No marketing page or hero section** | Build test | **PASS** | Root `/` routes directly to full chat application. Marketing components completely deleted. |
| 5 | **No emojis anywhere in source or UI** | `check:rules` | **PASS** | Emojis in feedback, buttons, and admin console replaced with accessible SVGs and text labels. |
| 6 | **No em dashes (U+2014)** | Node Scanner | **PASS** | 0 em dashes found across all source, public, HTML, and user-facing backend strings. |
| 7 | **No scroll animations / hijacking** | `check:rules` | **PASS** | `scroll-behavior: smooth` removed; instant accessible jumping on stream and chat navigation. |
| 8 | **No cursor effects or streaming caret** | `check:rules` | **PASS** | `cursor-blink` keyframe and custom cursor utilities eradicated. |
| 9 | **No AI-slop graphics / illustrations** | Assets Audit | **PASS** | No robots, sparkles, or brain graphics. Plain text wordmark and solid `#0B5CAD` SVG cap icon only. |
| 10 | **No AI buzzwords / slop copy** | `check:rules` | **PASS** | Plain, sentence-case copy stating facts and next steps. |
| 11 | **No "Made with" badges** | Node Scanner | **PASS** | Case-insensitive search confirms zero builder badges in repo or build output. |
| 12 | **No dead controls** | Code Review | **PASS** | Every button, link, and toggle is connected to an active handler or not rendered. All `alert()` and `confirm()` replaced with `Dialog` and `Toast`. |

---

## 4. Manual QA Matrix

| Feature | Test Case | Expected Result | Result |
|---|---|---|---|
| **Chat Stream** | Send question "What is the BBA fee per semester?" | Streams chunks smoothly; collapsible sources disclosure shows handbook name and page; follow-up questions render. | PASS |
| **Stop Generation** | Click "Stop" during active SSE streaming | Stream immediately aborts via `AbortController`; partial message remains; composer re-enables. | PASS |
| **Cold Start Warning** | Request takes >4s without first byte | Inline notice: "Waking up server (Render cold start)..." appears calmly. | PASS |
| **Guest Mode Limit** | Send 4 messages without logging in | Message counter updates; 4th message displays accessible `GuestLimitModal` inviting sign up. | PASS |
| **Sidebar Management** | Rename thread to "BBA Fees 2026", delete thread | Rename saves inline; delete opens `Dialog` confirmation; sidebar updates without reload. | PASS |
| **Theme Toggle** | Switch System -> Light -> Dark | Theme updates instantly; inline script in `index.html` prevents white flash on refresh. | PASS |
| **Admin Overview** | Switch between 7, 30, and 90 day ranges | Pure SVG bar and line charts re-render cleanly without external charting libraries. | PASS |
| **Admin Gaps** | Update workflow status to "in_progress", add note | Persists to MongoDB via `PATCH /api/admin/knowledge-gaps/review-status`; CSV exports with UTF-8 BOM. | PASS |
| **Admin Conversations**| Click "Reveal" on masked email | Audited email reveal executes; audit event logged; transcript drawer slides over with message details. | PASS |
| **Admin Users** | Attempt to delete own account | Blocked with notification: "You cannot delete your own admin account"; deleting other user cascades. | PASS |
| **Settings Export** | Click "Export JSON" in Settings | Browser downloads `charusat_conversations_<date>.json` containing all user threads and messages. | PASS |
| **Settings Clear** | Click "Clear history" | Opens `Dialog`; upon confirmation, calls `DELETE /api/conversations` and clears chat feed. | PASS |

---

## 5. Deployment Instructions

### A. Backend Deployment (Render Free Web Service)
1. **Branch:** Push all commits from `redesign/chat-first` to origin and merge into the `deploy` branch.
2. **Configuration (`render.yaml`):**
   - Root directory: `backend`
   - Build command: `chmod +x build.sh && ./build.sh`
   - Start command: `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
3. **Environment Variables (Set in Render Dashboard):**
   - `GOOGLE_API_KEY`: Primary Gemini 2.5 Flash API key.
   - `GROQ_API_KEY`: Failover Groq API key (`openai/gpt-oss-120b`).
   - `MONGODB_URI`: Production MongoDB Atlas connection string.
   - `JWT_SECRET`: High-entropy 64+ char random secret (system startup assertion fails if default).
   - `DEV_AUTO_LOGIN`: `false` (enforced by production assertion).
   - `FRONTEND_URL`: Production Vercel URL (for strict CORS header).

### B. Frontend Deployment (Vercel SPA)
1. **Build Settings:**
   - Framework preset: `Vite`
   - Root directory: `frontend` (or project root with `vercel.json` rewrites)
   - Build command: `npm run build` (runs `node scripts/check-rules.mjs && vite build`)
   - Output directory: `dist`
2. **Environment Variables (Set in Vercel Dashboard):**
   - `VITE_API_URL`: Full HTTPS URL of the deployed Render backend (e.g. `https://charusat-chatbot-api.onrender.com`).
   - `VITE_GOOGLE_CLIENT_ID`: Google OAuth Web Client ID for student sign-in.
3. **Headers & Security:**
   - Security headers in `vercel.json` enforce CSP, nosniff, frame denial, and 1-year immutable caching on static assets.
