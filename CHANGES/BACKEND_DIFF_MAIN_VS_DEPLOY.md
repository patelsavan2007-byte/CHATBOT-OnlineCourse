# CHARUSAT Online Course Assistant: Backend Differences (deploy vs main)

This document provides a comprehensive, component-by-component summary of all backend differences between the **`deploy`** branch and the **`main`** branch.

---

## 1. Executive Summary

| Attribute | `deploy` Branch Backend | `main` Branch Backend |
| :--- | :--- | :--- |
| **Architectural Model** | **Stateless RAG Microservice** | **Stateful Authenticated Platform** |
| **API Version** | `1.0.0` | `2.0.0` |
| **Database & Persistence** | **None** (No database; conversations exist only in frontend memory or ephemeral state) | **MongoDB Atlas** integration (`charusat_assistant` database) with collections for users, conversations, and messages |
| **User Authentication** | **None** (Public anonymous access only) | **Full Auth Subsystem**: Email/Password (bcrypt), JWT (HS256), Google OAuth token verification, Dev auto-login |
| **Chat Sessions & History** | Single-shot stateless queries via `POST /chat` | Persistent multi-session threads via `POST /api/chat`, with guest mode (message limit) & guest-to-user migration (`/api/chat/migrate`) |
| **Conversation Management** | None | Full CRUD: list, create, view with messages, rename, and delete conversation threads |
| **Administration** | None | Role-based access control (`user` vs `admin`), dev admin auto-seeding, and `/api/admin/stats` |
| **Core RAG Engine** | FastEmbed + ChromaDB + Gemini / Groq Llama 3.3 70B | **100% Identical** (Retriever, Scraper, Prompt, Fallback LLM, Conflict Resolution, Source Authority untouched) |
| **Backward Compatibility** | Original baseline | **100% Preserved** (All original endpoints `/chat`, `/health`, `/programs`, `/sources`, `/refresh` still function) |

---

## 2. File Differences Overview

### File Status Matrix

| File Path | Status | Impact / Purpose |
| :--- | :---: | :--- |
| `backend/api.py` | **MODIFIED** | Mounted 4 new routers (`auth`, `conversations`, `chat`, `admin`), added MongoDB init & dev-admin seeding, bumped version to 2.0.0. Kept all legacy endpoints. |
| `backend/requirements.txt` | **MODIFIED** | Added 5 production dependencies for MongoDB, JWT, and password hashing. |
| `backend/app/database.py` | **NEW** | MongoDB connection management (PyMongo), index creation, and graceful fallback when offline. |
| `backend/app/auth.py` | **NEW** | Bcrypt hashing, JWT encode/decode, FastAPI dependencies (`get_current_user`, `get_optional_user`, `require_admin`), Google token verification. |
| `backend/app/models.py` | **NEW** | MongoDB data access layer and schemas for `users`, `conversations`, and `messages`. Title generator & cascade deletion. |
| `backend/app/routes/__init__.py` | **NEW** | Package marker for router modules. |
| `backend/app/routes/auth_routes.py` | **NEW** | Auth endpoints: signup, login, logout, me, Google OAuth, dev auto-login. |
| `backend/app/routes/chat_routes.py` | **NEW** | Persistent chat endpoint (`/api/chat`) supporting guest and authenticated users, plus session migration (`/api/chat/migrate`). |
| `backend/app/routes/conversation_routes.py` | **NEW** | Thread management endpoints: list, create, get thread with history, rename, delete. |
| `backend/app/routes/admin_routes.py` | **NEW** | Admin stats endpoint (`/api/admin/stats`). |
| `.env.example` (Root) | **MODIFIED** | Added configuration keys for MongoDB, JWT, Admin email, Dev auto-login, Guest limit, and Google OAuth. |
| `backend/vector_db/*` | **UPDATED** | Vector database files reflecting indexing updates (core embeddings unchanged). |
| *All Core RAG Files* (`chatbot.py`, `llm.py`, `retriever.py`, `rag_chain.py`, `prompt.py`, `config.py`, `utils.py`, `embeddings.py`, `scraper.py`, `source_authority.py`, `conflict.py`, `deduplicate.py`) | **UNCHANGED** | Zero modifications. The core retrieval and generative AI pipeline functions identically on both branches. |

---

## 3. Detailed Component Breakdown

### 3.1. `backend/api.py` (Main Application Entrypoint)
* **On `deploy`:**
  * Initialized RAG pipeline (`build_rag_chain()`).
  * Defined FastAPI app (`version="1.0.0"`).
  * Provided endpoints: `POST /chat`, `GET /health`, `GET /programs`, `GET /sources`, `POST /refresh`.
  * No external database initialization or user sessions.
* **On `main`:**
  * Upgraded version to `2.0.0`.
  * Added non-blocking MongoDB connection initialization on startup (`init_mongodb()`). If MongoDB is not configured or unavailable, the backend logs a warning and gracefully degrades without crashing.
  * Added developer admin seeding (`seed_dev_admin()`) if `DEV_AUTO_LOGIN` is enabled.
  * Mounted 4 new modular routers:
    * `app.include_router(auth_router)`
    * `app.include_router(conversation_router)`
    * `app.include_router(chat_router)`
    * `app.include_router(admin_router)`
  * Preserved all original endpoints (`/chat`, `/health`, `/programs`, `/sources`, `/refresh`) intact for backwards compatibility.

---

### 3.2. `backend/app/database.py` (MongoDB Layer - NEW)
* **Features:**
  * Synchronous MongoDB connection using `pymongo.MongoClient` with 5000ms connect/selection timeouts.
  * Configurable via `MONGODB_URI` environment variable. Database name: `charusat_assistant`.
  * Graceful fallback: If `MONGODB_URI` is empty or connection fails, returns `None` so the RAG chatbot continues to answer questions without crashing.
  * Automatic index creation (`_ensure_indexes`):
    * `users`: Unique index on `email`, sparse index on `google_id`.
    * `conversations`: Compound index on `("user_id", 1), ("updated_at", -1)`.
    * `messages`: Compound index on `("conversation_id", 1), ("created_at", 1)`.

---

### 3.3. `backend/app/auth.py` (Authentication & Security - NEW)
* **Features:**
  * **Password Hashing:** Passwords hashed with `bcrypt` (truncated safely to 72 bytes) with salt generation.
  * **JWT Tokens:** HS256 algorithm, 7-day expiration (`JWT_EXPIRATION_HOURS = 24 * 7`). Reads `JWT_SECRET` from environment with a development fallback.
  * **FastAPI Dependencies:**
    * `get_current_user`: Strict authentication check via HTTP Bearer token. Returns 401 Unauthorized if token is missing or expired.
    * `get_optional_user`: Permissive authentication check. Returns user dictionary if valid token provided, or `None` if guest/unauthenticated (enables dual guest/user endpoints).
    * `require_admin`: Verifies that the authenticated user possesses the `role == "admin"` attribute; returns 403 Forbidden otherwise.
  * **Google OAuth Verification:** Asynchronous token verification using Google's public `https://oauth2.googleapis.com/tokeninfo` endpoint via `httpx`, verifying token audience (`aud == GOOGLE_CLIENT_ID`).
  * **Development Auto-Login Bypass:** Allows fast local frontend testing without credentials when `DEV_AUTO_LOGIN=true` and `ADMIN_EMAIL` is set.

---

### 3.4. `backend/app/models.py` (Data Access Layer - NEW)
* **Collections & Functions:**
  * **`users`:**
    * `create_user(...)`, `find_user_by_email(...)`, `find_user_by_id(...)`, `find_user_by_google_id(...)`, `update_user(...)`, `get_user_count(...)`.
    * Fields: `name`, `email`, `password_hash`, `google_id`, `avatar`, `role`, `created_at`, `updated_at`.
  * **`conversations`:**
    * `create_conversation(...)`, `get_user_conversations(...)`, `get_conversation(...)`, `update_conversation(...)`, `delete_conversation(...)`, `get_conversation_count(...)`.
    * Automatic title generator (`generate_conversation_title(...)`) that creates clean, readable thread names from the first user question.
    * Cascade deletion: Deleting a conversation automatically purges all child messages from the `messages` collection.
  * **`messages`:**
    * `create_message(...)`, `get_conversation_messages(...)`.
    * Stores role (`user` / `assistant`), message text content, source citations array, and timestamp.
    * Automatically bumps the parent conversation's `updated_at` timestamp.

---

### 3.5. `backend/app/routes/` (API Endpoints - NEW)

#### Auth Routes (`app/routes/auth_routes.py`)
* `POST /api/auth/signup`: Registers new user, checks existing email, hashes password, assigns `admin` role if email matches `ADMIN_EMAIL`, returns JWT + user profile.
* `POST /api/auth/login`: Validates email and bcrypt password hash, returns JWT + user profile.
* `POST /api/auth/logout`: Endpoint acknowledging logout (client discards token).
* `GET /api/auth/me`: Returns current user profile (requires Bearer token).
* `POST /api/auth/google`: Verifies Google ID token, links Google ID to existing account or creates new user, returns JWT.
* `POST /api/auth/dev-login`: Bypasses login in development mode only (blocked if `ENVIRONMENT=production`).

#### Chat Routes (`app/routes/chat_routes.py`)
* `POST /api/chat`:
  * **Guest Mode:** If no auth token provided, runs RAG pipeline and returns answer + sources without database writes.
  * **Authenticated Mode:** If user is logged in, auto-creates or looks up conversation, runs RAG pipeline, stores both user query and assistant response (with citations) in MongoDB, and returns answer + conversation ID + message ID + sources.
* `POST /api/chat/migrate`:
  * Enables a seamless transition for guest users: when an unauthenticated user has chatted up to the guest limit and decides to sign up/log in, their local browser messages are sent here and inserted into a newly created MongoDB conversation under their new account.

#### Conversation Routes (`app/routes/conversation_routes.py`)
* `GET /api/conversations`: Returns all conversation threads belonging to the authenticated user, sorted by most recent activity.
* `POST /api/conversations`: Creates a new blank conversation thread.
* `GET /api/conversations/{id}`: Retrieves specific conversation metadata and all historical messages in chronological order.
* `PATCH /api/conversations/{id}`: Renames the conversation title.
* `DELETE /api/conversations/{id}`: Deletes the conversation and its messages.

#### Admin Routes (`app/routes/admin_routes.py`)
* `GET /api/admin/stats`: Requires admin role (`require_admin`). Returns user count, conversation count, MongoDB connectivity status, and RAG pipeline readiness status.

---

### 3.6. `backend/requirements.txt` (Dependencies)

The following 5 packages were added to support authentication and MongoDB persistence:

```diff
  fastapi>=0.115.0
  uvicorn>=0.30.0
  gunicorn>=21.2.0
  python-multipart>=0.0.9
+ pymongo>=4.6.0
+ PyJWT>=2.8.0
+ passlib[bcrypt]>=1.7.4
+ python-jose[cryptography]>=3.3.0
+ httpx>=0.27.0
```

---

### 3.7. Environment Variables (`.env.example`)

New configuration keys introduced on `main`:

| Key | Purpose | Default / Fallback Behavior |
| :--- | :--- | :--- |
| `MONGODB_URI` | MongoDB Atlas connection string | If empty, database persistence is disabled gracefully |
| `JWT_SECRET` | Secret key for signing and verifying JWT tokens | Dev fallback default if not configured |
| `ADMIN_EMAIL` | Email that automatically receives the `admin` role | Empty / standard user role |
| `DEV_AUTO_LOGIN` | Enables auto-login endpoint for fast local testing | `false` |
| `GUEST_MESSAGE_LIMIT` | Max messages allowed for unauthenticated visitors | `4` |
| `GOOGLE_CLIENT_ID` | Client ID for Google OAuth token verification | Optional; Google auth disabled if unset |
| `GOOGLE_CLIENT_SECRET` | Client Secret for Google OAuth | Optional |

---

## 4. Summary Table of All API Endpoints

| Method | Path | Branch | Auth Required | Purpose |
| :---: | :--- | :---: | :---: | :--- |
| `POST` | `/chat` | Both | No | Legacy stateless RAG Q&A |
| `GET` | `/health` | Both | No | System health and RAG readiness |
| `GET` | `/programs` | Both | No | Available degree programs list |
| `GET` | `/sources` | Both | No | Ingested document sources list |
| `POST` | `/refresh` | Both | No | Reload Chroma vector database |
| `POST` | `/api/auth/signup` | `main` | No | User registration with email/password |
| `POST` | `/api/auth/login` | `main` | No | User login with email/password |
| `POST` | `/api/auth/logout` | `main` | No | Logout acknowledgement |
| `GET` | `/api/auth/me` | `main` | **Yes** (Bearer) | Get authenticated user profile |
| `POST` | `/api/auth/google` | `main` | No | Google OAuth signin/signup |
| `POST` | `/api/auth/dev-login` | `main` | Dev Only | Instant admin auto-login for testing |
| `POST` | `/api/chat` | `main` | **Optional** | Stateful chat (saves to Mongo if auth, stateless if guest) |
| `POST` | `/api/chat/migrate` | `main` | **Yes** (Bearer) | Migrates guest messages to user account |
| `GET` | `/api/conversations` | `main` | **Yes** (Bearer) | List all conversations for user |
| `POST` | `/api/conversations` | `main` | **Yes** (Bearer) | Create a new conversation thread |
| `GET` | `/api/conversations/{id}` | `main` | **Yes** (Bearer) | Retrieve conversation and full message history |
| `PATCH` | `/api/conversations/{id}` | `main` | **Yes** (Bearer) | Rename conversation title |
| `DELETE` | `/api/conversations/{id}` | `main` | **Yes** (Bearer) | Delete conversation and all its messages |
| `GET` | `/api/admin/stats` | `main` | **Admin** | System statistics (users, chats, DB status) |

---

## 5. Conclusion

The `main` branch backend preserves 100% of the retrieval-augmented generation functionality developed on `deploy`, while introducing a production-ready application architecture:
1. **User Authentication & Authorization** (Email/Password, Google OAuth, Admin role).
2. **Persistent Storage** with MongoDB Atlas (Users, Conversations, Messages).
3. **Seamless UX Flows** (Guest message limit with migration upon signup, conversation renaming, history browsing).
4. **Resilience & Fallback** (Continues serving RAG responses even if MongoDB is temporarily down).
