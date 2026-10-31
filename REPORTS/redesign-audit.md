# Redesign Audit - Phase 0 (Read-Only)

**Date:** 2026-10-28
**Branch:** read-only scan, no code changed

---

## 1. What Exists

### Frontend (frontend/src)

| File | Purpose | Decision |
|------|---------|----------|
| `App.jsx` | Root router. Hard-coded dark styles in AppLoader and NotFound. | Change |
| `index.css` | Tokens + animations. Dark-first. Has `scroll-behavior: smooth`, `cursor-blink`, `float`, `glow-pulse`, `shimmer`, `noise-overlay`, `.glass`, `backdrop-filter`, 9999px chips. Accent is indigo/violet. | Rewrite |
| `index.html` | Inline indigo favicon. Google Fonts (IP leak). No theme script. No OG tags. | Rewrite |
| `pages/Landing.jsx` | 426-line marketing page. Linear gradients, blur glow, rounded-full pills, floating animation, indigo colors. "Official information" claim. | Delete |
| `pages/Chat.jsx` | Good structure. `receivedChunk` used undeclared (line 144, bug). No Stop button. No cold-start warning. | Fix |
| `pages/Admin.jsx` | Hard-coded dark. Emoji thumbs on lines 265-266, 376, 381. `alert()` + `window.confirm()` on lines 106, 111, 117. Indigo classes. "User Satisfaction" mislabels `feedback_rate`. CSV uses relative URL (line 92, cross-origin fail). No UTF-8 BOM, no formula-injection guard. | Major rewrite |
| `pages/Login.jsx` | "Forgot password?" with empty onClick (dead control, line 168). Hard-coded NAAC/UGC/NIRF claims (lines 97-101). DM Serif font. | Fix |
| `pages/Settings.jsx` | Missing theme picker, typing toggle, data export, delete account. `rounded-full` avatar. No legal links. | Expand |
| `pages/AdminLogin.jsx` | Likely hard-coded dark. | Fix |
| `components/chat/ChatLayout.jsx` | Good. `backdrop-blur-sm` on overlay (banned). No skip link. | Fix |
| `components/chat/ChatComposer.jsx` | Good char limit, IME, auto-resize. No Stop button. `rounded-2xl` (spec = 12px). | Fix |
| `components/chat/AssistantMessage.jsx` | Avatar file missing. `rounded-full` on buttons (lines 162, 244). No sources panel. | Fix |
| `components/chat/MessageList.jsx` | `scrollIntoView({ behavior: "smooth" })` line 70 (banned). `rounded-full` FAB (line 119). | Fix |
| `components/chat/WelcomeScreen.jsx` | `animate-glow` (banned). `--tint-indigo` token. | Fix |
| `components/site/SiteNav.jsx` | Marketing nav. | Delete |
| `components/site/SiteFooter.jsx` | Marketing footer. | Delete |
| `components/ui/ErrorBoundary.jsx` | Likely hard-coded dark. | Fix |
| `components/RichText.jsx` | Markdown renderer. No image domain allowlist. | Fix |
| `contexts/ThemeContext.jsx` | No inline script before paint -- flash on load. | Fix |
| `hooks/useChat.js` | `receivedChunk` undeclared line 144. No AbortController. Dead thinking timer lines 117-119. | Fix |
| `config/branding.js` | `ASSISTANT_AVATAR = "/assistant-avatar.svg"` -- file missing. | Fix |

### Backend

| File | Issues |
|------|--------|
| `api.py` | `CORSMiddleware(allow_origins=["*"])`. No startup assertions. Legacy `/chat` line 203 destructures object as tuple (TypeError). |
| `chat_routes.py` | Lines 443, 490: `pass  # _log_chat_event removed` -- events never written, dashboard stale. Lines 385-395: mojibake ellipsis in status strings. Line 792: duplicate `"message"` key in dict. No `max_length` on question. |
| `admin_routes.py` | Lines 86-100: plain `==` password compare, default `"admin123"`. CSV: no BOM, no injection guard, relative URL. Stats reads empty `db.chat_events`. |
| `auth_routes.py` | dev-login production check relies on env vars Render does not set. |
| `auth.py` | JWT secret falls back silently. `seed_dev_admin()` defaults password to `"admin123"`. No disabled-user check. |

---

## 2. What Will Be Removed

- `frontend/src/pages/Landing.jsx`
- `frontend/src/components/site/SiteNav.jsx`
- `frontend/src/components/site/SiteFooter.jsx`
- From `index.css`: keyframes `float`, `glow-pulse`, `cursor-blink`, `shimmer`; utilities `.animate-glow`, `.animate-float`, `.glass`, `.noise-overlay`; `backdrop-filter`; `scroll-behavior: smooth`; `border-radius: 9999px` on scrollbar; indigo/violet accent tokens; `::selection` indigo color; `.suggestion-chip` 9999px radius
- Google Fonts link tags and DM Serif Display from `index.html`
- Inline data-URI favicon

---

## 3. Bugs Found

### Frontend

| # | File | Line | Bug |
|---|------|------|-----|
| F1 | `useChat.js` | 144 | `receivedChunk` used but never declared (ReferenceError) |
| F2 | `AssistantMessage.jsx` | 9 | `/assistant-avatar.svg` file missing, broken img |
| F3 | `MessageList.jsx` | 70 | `scrollIntoView({ behavior: "smooth" })` banned |
| F4 | `Admin.jsx` | 92 | CSV export uses relative URL, fails cross-origin |
| F5 | `Admin.jsx` | 106, 111, 117 | `alert()` and `window.confirm()` must be replaced |
| F6 | `Admin.jsx` | 260-266 | "User Satisfaction" mislabels `feedback_rate` |
| F7 | `Admin.jsx` | 265-266 | Emoji in source (rule 5) |
| F8 | `Admin.jsx` | 376, 381 | Emoji in JSX (rule 5) |
| F9 | `Login.jsx` | 168 | "Forgot password?" empty onClick (dead control, rule 12) |
| F10 | `Login.jsx` | 97-101 | NAAC/UGC/NIRF claims without source citation (rule 3) |
| F11 | `WelcomeScreen.jsx` | 60 | `animate-glow` banned |
| F12 | `index.css` | 156 | `scroll-behavior: smooth` (rule 7) |
| F13 | `index.css` | 264-267 | `@keyframes cursor-blink` (rule 8) |
| F14 | `index.css` | 259-262 | `@keyframes float` (rule 7) |
| F15 | `index.css` | 254-257 | `@keyframes glow-pulse` (rule 7) |
| F16 | `index.css` | 249-252 | `@keyframes shimmer` (rule 7) |
| F17 | `index.css` | 301-310 | `.skeleton` linear-gradient (rule 1) |
| F18 | `index.css` | 403 | `.suggestion-chip` 9999px radius (rule 2) |
| F19 | `index.css` | 440-448 | `.glass` backdrop-filter (rule 7) |
| F20 | `index.css` | 428-435 | `.noise-overlay` (rule 7) |
| F21 | `index.css` | 18-83 | Default theme uses indigo `#6366f1` (rule 1) |
| F22 | `index.css` | 110-114 | Light theme uses indigo `#4338ca` and violet `#6d28d9` (rule 1) |
| F23 | `index.html` | 7 | Favicon indigo fill `#818cf8` (rule 1) |
| F24 | `index.html` | 16-21 | Google Fonts link tags (IP leak) |
| F25 | `index.html` | 15 | Title `--` (confirm if U+2014 em dash) |
| F26 | `App.jsx` | 29, 45 | AppLoader and NotFound hard-code `bg-slate-950` (not themed) |
| F27 | `App.jsx` | 32 | AppLoader `fill-indigo-400` (rule 1) |
| F28 | `Landing.jsx` | 175 | `linear-gradient` in inline style (rule 1) |
| F29 | `Landing.jsx` | 179 | Glassmorphism blur glow (rule 7) |
| F30 | `ChatComposer.jsx` | 150 | `rounded-2xl` on composer (spec = 12px radius) |
| F31 | `ChatLayout.jsx` | 108 | `backdrop-blur-sm` on overlay (banned) |
| F32 | `useChat.js` | 117-119 | Dead thinking timer, only re-sets isLoading(true) |
| F33 | -- | -- | No inline theme script in index.html, flash on load |
| F34 | `AssistantMessage.jsx` | 162 | `rounded-full` on quick reply buttons (rule 2) |
| F35 | `AssistantMessage.jsx` | 244 | `rounded-full` on suggested question buttons (rule 2) |
| F36 | `MessageList.jsx` | 119 | `rounded-full` on scroll FAB (circles OK per spec for functional UI) |
| F37 | `ChatLayout.jsx` | -- | No skip-to-main-content link |
| F38 | `ThemeContext.jsx` | -- | Theme via React state, applied after paint |

### Backend

| # | File | Line | Bug |
|---|------|------|-----|
| B1 | `chat_routes.py` | 443, 490 | Chat events never written, dashboard forever stale |
| B2 | `chat_routes.py` | 385-395 | Mojibake ellipsis in status strings |
| B3 | `chat_routes.py` | 792 | Duplicate `"message"` key in correction response |
| B4 | `chat_routes.py` | 60 | No `max_length` on question field |
| B5 | `admin_routes.py` | 86-100 | Plain `==` password compare + default `"admin123"` |
| B6 | `admin_routes.py` | 191-221 | CSV: no BOM, no injection guard, relative URL |
| B7 | `api.py` | 131-137 | `allow_origins=["*"]` |
| B8 | `api.py` | 203 | Legacy `/chat` destructures RAG result object as tuple (TypeError) |
| B9 | `auth.py` | 36-41 | JWT secret falls back silently |
| B10 | `auth.py` | 201 | Default ADMIN_PASSWORD = "admin123" |
| B11 | `auth_routes.py` | 242 | dev-login production check unreliable on Render |
| B12 | `admin_routes.py` | 127-131 | Stats queries always-empty `db.chat_events` |

---

## 4. What Will Be Added

**Frontend:** `src/config/site.js`, `scripts/check-rules.mjs`, `pages/About.jsx`, `pages/Privacy.jsx`, `pages/Terms.jsx`, favicons, web manifest, inline theme script, @fontsource packages, Stop button, cold-start warning, Sources panel, Dialog component, Toast component, Admin tabs (Conversations, Knowledge Base, Audit Log).

**Backend:** pytest tests per new route, restored `_log_chat_event`, `GET /api/me/export`, `DELETE /api/me`, `PATCH /api/admin/gaps/:id`, `GET /api/admin/conversations`, `GET /api/admin/audit-log`, `PATCH /api/admin/feedback/:id`, `PATCH /api/admin/users/:id`, `DELETE /api/admin/users/:id`, `GET /api/admin/knowledge-base`, `reason` field on feedback, audit log collection.

---

## 5. Git .env Check

`backend/.env` was committed in `2cc24c70` (Jul 27) and removed in `3d76ebc6` (Aug 2). Content from `git show 2cc24c70:backend/.env`:

```
# Set either GOOGLE_API_KEY or OPENAI_API_KEY to use a hosted LLM.
# GOOGLE_API_KEY=
# OPENAI_API_KEY=
```

**Result:** Commented-out examples only. No real secrets. No key rotation required. Confirm both `backend/.gitignore` and `frontend/.gitignore` cover `.env` so they cannot be re-committed.

---

## 6. "Made with" Check

No `"made with"` string found in any source, public, or config file in this repository.

If Vercel injects "Powered by Vercel" on the deployed site, disable it at: **Vercel Dashboard > Project > Settings > General > Vercel Branding**.

---

## 7. Phase Plan

**Phase 1 (Foundations):** New design tokens in `index.css`; @fontsource install; inline theme script; delete Landing, SiteNav, SiteFooter; create `site.js`; create `check-rules.mjs`; create branch `redesign/chat-first`.

**Phase 2 (Chat experience):** Fix all F-series bugs. Add AbortController Stop. Cold-start warning. Sources panel. Skip link. Rebuild WelcomeScreen and AssistantMessage. Fix all radius and animation violations.

**Phase 3 (Backend + admin):** Fix all B-series bugs. Add all new backend routes with tests. Build full 8-tab admin console.

**Phase 4 (Auth + legal + 404):** Remove dead controls and unverified claims. Add About, Privacy, Terms. Expand Settings. Fix AppLoader/NotFound theming.

**Phase 5 (Launch hardening):** Favicons. vercel.json security headers. Resolve all CONFIRM placeholders. Launch checklist.

**Phase 6 (Verification):** npm run build + check:rules clean. pytest green. Playwright at 360/768/1280px in light/dark as guest/user/admin. Lighthouse >= 95. Zero console errors.
