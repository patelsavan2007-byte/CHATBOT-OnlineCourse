# CHARUSAT Online Course Chatbot — Deployment Guide

Shareable frontend for the CHARUSAT Online Course Assistant chatbot.  
Deploy the **frontend to Vercel** and keep the **backend running locally** (or on a cloud VM).

---

## Prerequisites

| Tool    | Version  | Install                                   |
|---------|----------|--------------------------------------------|
| Node.js | ≥ 18     | https://nodejs.org                         |
| Python  | ≥ 3.10   | Already installed (for backend & smoke test) |
| ngrok   | latest   | https://ngrok.com/download (free account)  |

---

## 1. Quick Local Preview

```bash
# From the project root
cd deployment

# Install dependencies
npm install

# Copy env and point to local backend
cp .env.example .env
# (edit .env if needed — default is http://localhost:8000)

# Start dev server
npm run dev
```

Open **http://localhost:5173** — the chatbot UI should load.  
Make sure the backend is running (`uvicorn api:app --reload --port 8000` in the `backend/` directory).

---

## 2. Make Backend Accessible (ngrok)

Your stakeholder needs to reach the backend from the internet.  
The simplest way is **ngrok**:

```bash
# In a new terminal
ngrok http 8000
```

ngrok will print a public URL like `https://abc123.ngrok-free.app`.  
Copy that URL and set it in `deployment/.env`:

```env
VITE_API_URL=https://abc123.ngrok-free.app
```

> **Note:** Free ngrok URLs change every time you restart ngrok.  
> For a stable subdomain, sign up for a free ngrok account and use `ngrok http --domain=your-name.ngrok-free.app 8000`.

---

## 3. Deploy Frontend to Vercel

### Option A: Vercel CLI (one command)

```bash
cd deployment
npx -y vercel --prod
```

When prompted:
- **Set up and deploy?** → Yes
- **Which scope?** → Your account
- **Link to existing project?** → No
- **Project name?** → `charusat-chatbot` (or any name)
- **In which directory is your code located?** → `./`
- **Override settings?** → No (Vercel auto-detects Vite)

After deployment, set the environment variable in Vercel:
1. Go to your project on https://vercel.com
2. **Settings → Environment Variables**
3. Add `VITE_API_URL` = your ngrok URL (e.g. `https://abc123.ngrok-free.app`)
4. **Redeploy** (Deployments → three dots → Redeploy)

### Option B: GitHub Integration

1. Push this repo to GitHub
2. Go to https://vercel.com/new
3. Import the repo
4. Set **Root Directory** to `deployment`
5. Add env variable `VITE_API_URL`
6. Deploy

---

## 4. Run Smoke Tests

Verify everything is working end-to-end:

```bash
# Test backend only (backend must be running)
python deployment/smoke_test.py --backend http://localhost:8000

# Test backend + deployed frontend
python deployment/smoke_test.py --backend https://abc123.ngrok-free.app --frontend https://charusat-chatbot.vercel.app
```

Expected output:
```
╔══════════════════════════════════════════════════╗
║   CHARUSAT Chatbot — Smoke Test Suite            ║
╚══════════════════════════════════════════════════╝

  Backend : http://localhost:8000

  ✔ PASS  Health check  status=ok  docs=444
  ✔ PASS  Root endpoint  GET / → 200

  ✔ PASS  Chat endpoint  session=abc12345…  answer_len=312  sources=3  llm=groq
  ✔ PASS  Follow-up (session continuity)  resolved_query="What are the fees for CHARUSAT online programmes?"
  ✔ PASS  Clear history  session abc12345… cleared

  All 5 tests passed ✓
```

---

## 5. Sharing the Demo Link

Once deployed, share this with your stakeholder:

```
https://charusat-chatbot.vercel.app
```

**Before the demo, make sure:**
- [ ] Backend is running locally (`uvicorn api:app --port 8000`)
- [ ] ngrok is tunnelling (`ngrok http 8000`)
- [ ] Vercel env variable `VITE_API_URL` points to the ngrok URL
- [ ] Smoke tests pass

---

## Project Structure

```
deployment/
├── .env.example        # Frontend environment template
├── index.html          # HTML entry point
├── package.json        # Node.js dependencies
├── README.md           # This file
├── smoke_test.py       # Endpoint verification script
├── vercel.json         # Vercel SPA routing config
├── vite.config.js      # Vite build configuration
└── src/
    ├── main.jsx        # React entry point
    ├── index.css       # Global styles (dark glassmorphism theme)
    └── App.jsx         # Chatbot UI component
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Chat shows "Offline" badge | Backend not running or ngrok not active |
| CORS errors in browser console | Backend already has `allow_origins=["*"]` — restart uvicorn |
| Chat takes too long | First request loads ML model (~40s cold start), subsequent are faster |
| ngrok URL changed | Update `VITE_API_URL` in Vercel env vars and redeploy |
| Smoke test `requests` not found | `pip install requests` in your venv |
