# CHARUSAT Online Programs — Frontend Redesign Walkthrough

## What Was Redesigned

Complete ground-up frontend redesign. Existing chatbot-centric UI replaced with a polished, production-quality university product consisting of a **Public Website** and a separate **Chat Application**.

---

## Routes

| Route | Status | Description |
|---|---|---|
| `/` | **Redesigned** | Editorial landing page — NO embedded chatbot |
| `/programs` | **New** | Program discovery: comparison table + level-grouped cards |
| `/programs/:slug` | **New** | Academic program detail: curriculum, eligibility, fees, sidebar |
| `/how-it-works` | **New** | RAG pipeline explanation, important disclaimers |
| `/faq` | **New** | Full FAQ accordion with topic filter chips |
| `/login` | **Redesigned** | Split-panel auth form with show/hide password |
| `/signup` | **Redesigned** | Password strength indicator + confirm mismatch validation |
| `/chat` | **Redesigned** | Clean ChatGPT/Claude-style chat app |
| `/chat/:conversationId` | **Preserved** | Load specific conversation |
| `/settings` | **Redesigned** | Account details, nav, sign-out |
| `/admin` | **Redesigned** | Stats dashboard — real `/api/admin/stats` connected |
| `/about` | → `/` | Legacy redirect |
| `/history` | → `/chat` | Legacy redirect |
| `/profile` | → `/settings` | Legacy redirect |

---

## Key Design Decisions

- **Homepage has NO chatbot** — pure editorial content about programs, how it works, FAQ, and trust signals
- **`?q=` URL param** — program detail pages link to `/chat?q=...` pre-seeding a question; Chat.jsx auto-sends it
- **Split public/app** — `/` `/programs` `/faq` `/how-it-works` use `SiteNav` + `SiteFooter` (white surface). `/chat` `/login` use dark `slate-950` surface
- **Design language:** DM Serif Display for editorial headings, Inter for UI; deep navy foundation with restrained indigo accents
- **No purple blobs, no AI gimmicks** — honest university information product

---

## New Files Created

```
src/
  data/
    programs.js           ← Real data from knowledge base (4 programs + 10 FAQ items)
  components/
    site/
      SiteNav.jsx         ← Transparent→solid scroll navbar, mobile menu
      SiteFooter.jsx      ← University-style dark footer
    chat/
      ChatComposer.jsx    ← Auto-resizing textarea, Enter-to-send
      MessageList.jsx     ← Auto-scroll, typing indicator
      UserMessage.jsx     ← Right-aligned bubble
      WelcomeScreen.jsx   ← Empty state with 4 clickable suggestions
      GuestLimitModal.jsx ← Sign-up modal on message limit
  pages/
    Programs.jsx          ← Comparison table + grouped program cards
    ProgramDetail.jsx     ← Syllabus, eligibility, info sidebar
    HowItWorks.jsx        ← RAG pipeline steps, disclaimers
    Faq.jsx               ← Topic-filtered accordion
```

---

## Redesigned Files

```
src/
  index.css                         ← Complete design system tokens, animations, scrollbars, prose
  App.jsx                           ← Updated routing with all new routes
  pages/
    Landing.jsx                     ← Full editorial redesign
    Login.jsx                       ← Split-panel design
    Signup.jsx                      ← Password strength + validation
    Chat.jsx                        ← ?q= URL param support added
    Settings.jsx                    ← Account management
    Admin.jsx                       ← Stats dashboard
  components/
    chat/
      Sidebar.jsx                   ← Date-grouped conversations, inline ConversationItem
      ChatLayout.jsx                ← Collapsible sidebar, mobile drawer
      AssistantMessage.jsx          ← Copy button, source chips, error state
    RichText.jsx                    ← Extended: numbered lists, h2/h3, conflict callout
    auth/
      ProtectedRoute.jsx            ← Passes location state for post-login redirect
  index.html                        ← Added DM Serif Display + Inter Google Fonts
```

---

## Deleted Files

| File | Replaced By |
|---|---|
| `components/Hero.jsx` | `pages/Landing.jsx` |
| `components/Programs.jsx` | `pages/Programs.jsx` |
| `components/HowItWorks.jsx` | `pages/HowItWorks.jsx` |
| `components/Faq.jsx` | `pages/Faq.jsx` |
| `components/Footer.jsx` | `components/site/SiteFooter.jsx` |
| `components/Navbar.jsx` | `components/site/SiteNav.jsx` |
| `components/ChatPanel.jsx` | Removed (no chatbot on landing) |
| `components/chat/ChatHeader.jsx` | Inlined in `ChatLayout.jsx` |
| `components/chat/ConversationList.jsx` | Inlined in `Sidebar.jsx` |
| `components/chat/ConversationItem.jsx` | Inlined in `Sidebar.jsx` |
| `components/auth/LoginForm.jsx` | Inlined in `Login.jsx` |
| `components/auth/SignupForm.jsx` | Inlined in `Signup.jsx` |
| `components/ui/LoadingSpinner.jsx` | Inline spinners |
| `components/ui/ErrorMessage.jsx` | Inline error UI |

---

## Backend Status

**No backend changes were made.** All API contracts preserved:

- Auth: `/api/auth/login`, `/api/auth/signup`, `/api/auth/logout`, `/api/auth/google`, `/api/auth/me`
- Chat: `/api/chat`, `/api/conversations`, `/api/conversations/:id`, `/api/chat/migrate`
- Admin: `/api/admin/stats`

---

## Running

| | URL |
|---|---|
| 🌐 **Frontend** | **http://localhost:5173** |
| 🤖 Main Backend | http://127.0.0.1:8000 |
| 📝 Swagger Docs | http://127.0.0.1:8000/docs |
| ⚙️ Deploy Backend | http://127.0.0.1:8001 |

---

## Known Limitations

| | |
|---|---|
| Password reset | No backend endpoint — button present but non-functional |
| Source file names | Raw filenames shown in citations (e.g. `online_mba`) |
| Admin user management | No `/api/admin/users` backend endpoint |
| Streaming responses | Backend doesn't stream — typing indicator used |
| Google Sign-In | Requires `VITE_GOOGLE_CLIENT_ID` in frontend `.env` |
