# CHARUSAT Online Course Chatbot — Deployment Guide

**Goal:** One public URL for your project guide. No laptop running. No ngrok.

**Architecture:** Render (backend) + Vercel (frontend) → guide opens Vercel URL.

---

## Prerequisites

| Tool | Purpose | Get it |
|------|---------|--------|
| GitHub account | Host the repo | Already set up |
| Render account | Host the backend | https://render.com (free) |
| Vercel account | Host the frontend | https://vercel.com (free) |

---

## Step 1 — Deploy Backend on Render

1. Go to **https://dashboard.render.com** → click **New +** → **Web Service**
2. Click **Connect a GitHub repository** → select `patelsavan2007-byte/CHATBOT-OnlineCourse`
3. Fill in these settings:

   | Setting | Value |
   |---------|-------|
   | **Name** | `charusat-chatbot-api` |
   | **Branch** | `deploy` |
   | **Root Directory** | `backend` |
   | **Runtime** | `Python 3` |
   | **Build Command** | `chmod +x build.sh && ./build.sh` |
   | **Start Command** | `gunicorn api:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120` |
   | **Plan** | `Free` |

4. Scroll down to **Environment Variables** → click **Add Environment Variable** for each:

   | Key | Value |
   |-----|-------|
   | `GOOGLE_API_KEY` | your actual Google Gemini API key |
   | `GROQ_API_KEY` | your actual Groq API key |

5. Click **Create Web Service**

> **Build time:** The first deploy takes 5–10 minutes. Render installs all dependencies and builds the ChromaDB vector database from the knowledge base files. You'll see logs in the Render dashboard.

6. Once deployed, you'll see a URL like: `https://charusat-chatbot-api.onrender.com`
   - Copy this URL — you'll need it in Step 2.
   - Test it: open `https://charusat-chatbot-api.onrender.com/health` in your browser. You should see `{"status":"ok","vector_store_documents":...}`

---

## Step 2 — Deploy Frontend on Vercel

1. Go to **https://vercel.com/new**
2. Click **Import Git Repository** → select `patelsavan2007-byte/CHATBOT-OnlineCourse`
3. Fill in these settings:

   | Setting | Value |
   |---------|-------|
   | **Framework Preset** | `Vite` (auto-detected) |
   | **Root Directory** | `deployment` |
   | **Branch** | `deploy` |

4. Expand **Environment Variables** → add:

   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | `https://charusat-chatbot-api.onrender.com` (your Render URL from Step 1) |

5. Click **Deploy**

> **Build time:** ~1 minute. Vercel builds the React app and serves it globally.

6. Once deployed, Vercel gives you a URL like: `https://charusat-chatbot.vercel.app`

---

## Step 3 — Share with Your Guide

Send your guide this single URL:

```
https://charusat-chatbot.vercel.app
```

That's it. They open it, see the chatbot, ask questions, get answers.

---

## ⚠ Free Tier Limitation: Cold Starts

Render's free tier **spins down after 15 minutes of inactivity**.

- First message after idle: ~30–90 second delay (Render wakes up + loads ML model)
- All subsequent messages: fast (2–5 seconds)

**Before your guide's demo session:** Open `https://charusat-chatbot-api.onrender.com/health` yourself to wake the server up. Wait for a `{"status":"ok"}` response, then tell your guide to open the chatbot.

---

## Smoke Test

After deployment, verify everything end-to-end:

```bash
# From the project root — requires: pip install requests
python deployment/smoke_test.py \
  --backend https://charusat-chatbot-api.onrender.com \
  --frontend https://charusat-chatbot.vercel.app
```

Expected output:
```
╔══════════════════════════════════════════════════╗
║   CHARUSAT Chatbot — Smoke Test Suite            ║
╚══════════════════════════════════════════════════╝

  ✔ PASS  Health check  status=ok  docs=444
  ✔ PASS  Root endpoint  GET / → 200
  ✔ PASS  Chat endpoint  session=abc12345…  answer_len=312  sources=3  llm=groq
  ✔ PASS  Follow-up (session continuity)  resolved_query="..."
  ✔ PASS  Clear history  session abc12345… cleared
  ✔ PASS  Frontend reachable  https://charusat-chatbot.vercel.app → 200

  All 6 tests passed ✓
```

---

## Updating the Deployment

Whenever you push to the `deploy` branch, both Render and Vercel **automatically redeploy**.

```bash
git add .
git commit -m "your message"
git push origin deploy
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Chatbot shows red "Offline" badge | Backend cold-starting — wait 60s and refresh |
| First message takes 90 seconds | Normal — cold start + model loading. Warn your guide beforehand. |
| Render build fails | Check Render logs. Most likely a missing env var. |
| Vercel shows blank page | Check that `Root Directory` is set to `deployment`, not the repo root |
| `VITE_API_URL` not working | Confirm no trailing slash in the URL, redeploy Vercel after changing env vars |
| Render shows "OOM" (out of memory) | Upgrade from Free to Starter ($7/month) for 512MB→512MB dedicated |

---

## Project Structure (relevant to deployment)

```
CHATBOT-OnlineCourse/          ← repo root
├── render.yaml                ← Render IaC config (tells Render how to deploy)
├── .env.example               ← template for backend env vars
│
├── backend/                   ← deployed to Render
│   ├── build.sh               ← Render build script (installs deps + builds vector DB)
│   ├── api.py                 ← FastAPI entry point (uvicorn api:app)
│   ├── requirements.txt       ← Python dependencies
│   ├── rebuild_vectordb.py    ← builds ChromaDB from knowledge_base/
│   ├── knowledge_base/        ← tracked in git (markdown + PDFs)
│   └── app/                   ← RAG pipeline modules
│
└── deployment/                ← deployed to Vercel
    ├── .env.example           ← template for frontend env vars
    ├── vercel.json            ← Vercel SPA routing
    ├── vite.config.js         ← Vite build config
    ├── package.json           ← Node dependencies
    ├── smoke_test.py          ← end-to-end verification script
    └── src/
        ├── main.jsx           ← React entry point
        ├── index.css          ← dark glassmorphism styles
        └── App.jsx            ← chatbot UI
```
