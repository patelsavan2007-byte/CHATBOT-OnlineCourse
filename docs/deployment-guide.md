# Deployment Guide: Vercel (Frontend) & Render (Backend)

This guide walks you through deploying the **CHARUSAT Online Course Chatbot** with the **React frontend on Vercel** and the **FastAPI + RAG backend on Render**.

---

## Architecture Overview

```mermaid
graph LR
    User[User Browser] -->|HTTPS| Vercel[Vercel: React + Vite Frontend]
    Vercel -->|REST API / CORS| Render[Render: FastAPI + RAG Backend]
    Render -->|Vector DB| ChromaDB[(Local ChromaDB ONNX)]
    Render -->|History & Auth| MongoDB[(MongoDB Atlas)]
    Render -->|LLM Inference| Gemini[Google Gemini / Groq API]
```

---

## 1. Prerequisites Checklist

Before you begin, have the following accounts and credentials ready:

1. **GitHub Repository**: All changes pushed to branch `main`.
2. **Render Account**: [https://render.com](https://render.com) (Free tier supported).
3. **Vercel Account**: [https://vercel.com](https://vercel.com) (Hobby/Free plan supported).
4. **MongoDB Atlas Account**: [https://cloud.mongodb.com](https://cloud.mongodb.com) (Free M0 cluster).
5. **LLM API Keys**:
   - **Google Gemini API Key**: [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   - **Groq API Key** (Failover): [https://console.groq.com/keys](https://console.groq.com/keys)

---

## 2. Deploy Backend on Render

You can deploy on Render either via **Blueprint** (automatic from `render.yaml`) or **Manual Web Service**.

### Option A: Via Blueprint (Fastest)

1. Go to your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub repository.
4. Render will detect `render.yaml`. It will automatically configure the service name, branch, root directory, build script, start command, and prompt for un-synced environment variables.
5. Fill in the required environment variables (see table below).
6. Click **Apply**.

### Option B: Manual Web Service

1. In Render Dashboard, click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the following settings:
   - **Name**: `charusat-chatbot-api` (or your choice)
   - **Region**: `Oregon (US West)` or `Frankfurt (EU)` (any region)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `chmod +x build.sh && ./build.sh`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. Under **Health Check Path**, enter: `/health`

---

### Backend Environment Variables on Render

In the Render Dashboard under **Environment** → **Environment Variables**, add:

| Key | Example / Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | `AIzaSy...` **(Required)** | Primary LLM key from Google AI Studio. |
| `GROQ_API_KEY` | `gsk_...` **(Required)** | Failover LLM key from Groq Console. |
| `JWT_SECRET` | `32+ random characters` **(Required)** | Secret key to sign auth tokens. *Do not leave as default or blank.* |
| `MONGODB_URI` | `mongodb+srv://user:pass@cluster.mongodb.net` **(Required)** | Atlas connection URI for auth & chat history. |
| `ADMIN_EMAIL` | `admin@charusat.ac.in` **(Required)** | Email receiving admin privileges upon signup. |
| `ADMIN_PASSWORD` | `YourStrongAdminPassword` **(Recommended)** | Password for administrative login. |
| `DEV_AUTO_LOGIN` | `false` **(Required)** | Must be `false` in production. |
| `GUEST_MESSAGE_LIMIT` | `4` **(Optional)** | Free message limit before prompting login. |
| `ALLOWED_ORIGINS` | `https://your-frontend.vercel.app` **(Optional)** | Additional allowed origins (`*.vercel.app` is pre-allowed). |
| `PYTHON_VERSION` | `3.11.9` **(Recommended)** | Python version for Render runtime. |
| `GOOGLE_CLIENT_ID` | `...apps.googleusercontent.com` **(Optional)** | If using Google OAuth login. |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-...` **(Optional)** | If using Google OAuth login. |

> [!CRITICAL]
> **MongoDB Atlas Network Access**:
> In MongoDB Atlas, go to **Network Access** → **IP Access List** → **Add IP Address** → click **Allow Access from Anywhere** (`0.0.0.0/0`).
> Render free-tier web services use dynamic IP addresses. Without `0.0.0.0/0`, your backend will fail to connect to MongoDB and time out.

Once deployed, copy your live Render URL (e.g., `https://charusat-chatbot-api.onrender.com`).

---

## 3. Deploy Frontend on Vercel

1. Go to your [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository.
4. In the **Configure Project** screen:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click **Edit** and select `frontend` (or leave default root `./`—both are supported by the project config).
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Expand **Environment Variables** and add:

| Key | Value | Notes |
|---|---|---|
| `VITE_API_URL` | `https://charusat-chatbot-api.onrender.com` | **Your live Render URL** *(Do NOT add trailing slash `/`)* |
| `VITE_GOOGLE_CLIENT_ID` | `172934942944-....apps.googleusercontent.com` | Optional (if using Google Login) |
| `VITE_GUEST_MESSAGE_LIMIT` | `4` | Guest message count limit |

6. Click **Deploy**.
7. In ~1 minute, Vercel will complete the build and assign a domain (e.g., `https://your-chatbot.vercel.app`).

---

## 4. Google OAuth Configuration (If using Google Login)

If you have configured Google Sign-in:

1. Open [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials).
2. Edit your **OAuth 2.0 Client ID**.
3. Under **Authorized JavaScript origins**, add:
   - `https://your-chatbot.vercel.app` (your actual Vercel domain)
   - `http://localhost:5173` (for local development)
4. Under **Authorized redirect URIs**, add the same domain if using redirect flows.
5. Click **Save**.

---

## 5. Free-Tier Operational Notes

1. **Cold Starts**: Render free instances enter sleep mode after 15 minutes of inactivity. When the first visitor accesses the site, the backend takes ~30–50 seconds to spin up. The frontend interface includes an automated notification banner informing the user that the server is waking up.
2. **Vector DB Loading**: The Chroma vector database is pre-built with ONNX embeddings (`bge-small-en-v1.5`), maintaining memory usage under ~120 MB RAM, well inside Render's 512 MB free tier ceiling.

