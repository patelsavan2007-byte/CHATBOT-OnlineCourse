"""FastAPI HTTP server for the CHARUSAT Online Course Assistant.

This module provides the chatbot HTTP API for the RAG-based Q&A assistant,
plus authentication, conversation management, and admin endpoints.

Run with::

    uvicorn api:app --reload --port 8000
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure the backend root is on sys.path so ``app.*`` imports work when
# running with ``uvicorn api:app`` from the backend directory.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import config
from app.config import ensure_directories
from app.utils import logger, print_info, print_warning

# -----------------------------------------------------------------------
# Application bootstrap — chatbot RAG pipeline (best-effort)
# -----------------------------------------------------------------------

ensure_directories()

# Try to initialise the RAG pipeline. If the vector store isn't ready,
# the chatbot endpoints will return a graceful error.
_rag_ready = False
try:
    from app.embeddings import EmbeddingStore
    from app.llm import LLMClient
    from app.rag_chain import RAGChain
    from app.retriever import RAGRetriever

    embedding_store = EmbeddingStore()
    try:
        vector_store = embedding_store.load_vector_store()
        count = vector_store._collection.count()
        if count == 0:
            raise ValueError("Vector store is empty")
        print_info(f"Loaded vector store with {count} documents.")
    except Exception as exc:
        print_warning(f"Vector store not ready ({exc}). Building vector store now...")
        try:
            from app.ingestion import KnowledgeBaseIngester
            ingester = KnowledgeBaseIngester()
            documents = ingester.load_documents()
            chunks = ingester.split_documents(documents)
            vector_store = embedding_store.build_vector_store(chunks)
            ingester.write_source_manifest()
            count = vector_store._collection.count()
            print_info(f"Vector store created with {count} documents.")
        except Exception as build_exc:
            print_warning(f"Failed to build vector store: {build_exc}. Chatbot will be unavailable.")
            vector_store = None

    if vector_store is not None:
        retriever = RAGRetriever(vector_store)
        llm_client = LLMClient()
        rag_chain = RAGChain(retriever, llm_client)
        _rag_ready = True

        # Check and log reranker status on startup
        _r_inst = getattr(retriever, "_reranker", None)
        _reranker_active = False
        _reranker_error = None
        if config.RERANKER_ENABLED:
            if _r_inst is None:
                _reranker_error = "Reranker instance was not initialized on retriever"
                logger.error("RERANKER STARTUP ERROR: %s", _reranker_error)
            elif _r_inst.model is None:
                _reranker_error = getattr(_r_inst, "load_error", "Failed to load reranker model")
                logger.error("RERANKER STARTUP ERROR: %s", _reranker_error)
            else:
                _reranker_active = True
                logger.info(
                    "Reranker startup check PASSED: active=%s (type=%s, model=%s)",
                    _reranker_active,
                    config.RERANKER_TYPE,
                    config.RERANKER_MODEL,
                )
        print_info(f"Reranker startup: active={_reranker_active}, error={_reranker_error}")
except Exception as rag_exc:
    print_warning(f"RAG pipeline init failed: {rag_exc}. Chatbot will be unavailable.")

# -----------------------------------------------------------------------
# MongoDB initialisation (best-effort)
# -----------------------------------------------------------------------

try:
    from app.database import init_mongodb
    _mongo_db = init_mongodb()
except Exception as mongo_exc:
    print_warning(f"MongoDB init failed: {mongo_exc}. Auth and chat history unavailable.")
    _mongo_db = None

# Seed dev admin user if configured
try:
    from app.auth import seed_dev_admin, is_dev_auto_login_enabled
    if is_dev_auto_login_enabled() and _mongo_db is not None:
        seed_dev_admin()
except Exception as seed_exc:
    print_warning(f"Dev admin seeding failed: {seed_exc}")

# -----------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------

app = FastAPI(
    title="CHARUSAT Online Course Assistant",
    description=(
        "CHARUSAT Online Course Assistant API:\n"
        "- RAG-based Q&A chatbot for CHARUSAT online degree programmes "
        "(fees, eligibility, duration, curriculum, admissions and more)\n"
        "- User authentication and conversation management\n"
    ),
    version="2.0.0",
)

def get_allowed_origins() -> List[str]:
    """Return restricted CORS allowed origins (localhost and configured production domains)."""
    origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    prod_domain = (os.getenv("PRODUCTION_DOMAIN") or "").strip()
    if prod_domain:
        if not prod_domain.startswith("http://") and not prod_domain.startswith("https://"):
            origins.append(f"https://{prod_domain}")
            origins.append(f"http://{prod_domain}")
        else:
            origins.append(prod_domain)
    extra = os.getenv("ALLOWED_ORIGINS", "")
    if extra:
        origins.extend([o.strip() for o in extra.split(",") if o.strip()])
    return list(dict.fromkeys(origins))


# Restrict CORS to localhost and production domain(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_security_checks():
    """Assert security requirements at startup."""
    env = os.getenv("ENVIRONMENT", os.getenv("NODE_ENV", "development")).lower()
    is_prod = env in ("production", "prod") or bool(os.getenv("RENDER") or os.getenv("VERCEL"))
    jwt_secret = os.getenv("JWT_SECRET", "").strip()
    dev_auto_login = os.getenv("DEV_AUTO_LOGIN", "false").strip().lower() in ("true", "1", "yes")

    if is_prod:
        if dev_auto_login:
            raise RuntimeError("CRITICAL SECURITY ERROR: DEV_AUTO_LOGIN must be false in production!")
        if not jwt_secret or jwt_secret == "charusat-dev-jwt-secret-change-in-production":
            raise RuntimeError("CRITICAL SECURITY ERROR: JWT_SECRET must be set to a secure secret in production!")


# -----------------------------------------------------------------------
# Mount new API routes
# -----------------------------------------------------------------------

from app.routes.auth_routes import me_router, router as auth_router
from app.routes.conversation_routes import router as conversation_router
from app.routes.chat_routes import router as chat_router
from app.routes.admin_routes import router as admin_router
from app.routes.suggest_routes import router as suggest_router

app.include_router(auth_router)
app.include_router(me_router)
app.include_router(conversation_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(suggest_router)

# -----------------------------------------------------------------------
# Chatbot Request / Response models (backward-compatible)
# -----------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Body for ``POST /chat``."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The user's question.",
    )
    history: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional conversation history for multi-turn Q&A.",
    )


class ChatResponse(BaseModel):
    """Response from ``POST /chat``.

    Only the assistant answer is returned to the client. Debug details
    (retrieved chunks, scores, LLM status) are written to the backend logs,
    not exposed in the API payload.
    """
    answer: str


class HealthResponse(BaseModel):
    """Response from ``GET /health``."""
    status: str
    vector_store_documents: int
    reranker_active: bool = False
    reranker_error: str | None = None


# -----------------------------------------------------------------------
# Chatbot Endpoints (backward-compatible — kept for existing integrations)
# -----------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Ask a question and return the assistant's answer."""
    logger.info("[CHAT] User query received: question=%r", request.question)

    if not _rag_ready:
        raise HTTPException(status_code=503, detail="Chatbot RAG pipeline is not available.")

    try:
        result = rag_chain.answer(request.question, history=request.history)
        answer_text = result.answer if hasattr(result, "answer") else str(result)
    except Exception as exc:
        logger.error("RAG chain failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate answer") from exc

    logger.info("[CHAT] Answer generated: %d chars", len(answer_text))
    logger.info("[CHAT] Request completed")
    return ChatResponse(answer=answer_text)


@app.get("/")
async def root():
    """Root endpoint welcoming users and pointing to docs."""
    return {
        "message": "CHARUSAT Online Course Assistant is running.",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Simple health check."""
    try:
        count = vector_store._collection.count() if _rag_ready else -1
    except Exception:
        count = -1

    reranker_active = False
    reranker_error = None
    if _rag_ready and hasattr(rag_chain, "retriever"):
        r = getattr(rag_chain.retriever, "_reranker", None)
        if r:
            reranker_active = bool(getattr(r, "model", None))
            reranker_error = getattr(r, "load_error", None) if not reranker_active else None

    return HealthResponse(
        status="ok",
        vector_store_documents=count,
        reranker_active=reranker_active,
        reranker_error=reranker_error,
    )


# -----------------------------------------------------------------------
# Public Question Bank & Contacts
# -----------------------------------------------------------------------

_cached_question_bank: Optional[List[Dict[str, Any]]] = None

def get_full_question_bank() -> List[Dict[str, Any]]:
    global _cached_question_bank
    if _cached_question_bank is not None:
        return _cached_question_bank
    qb_path = ROOT / "app" / "data" / "question_bank.json"
    if not qb_path.exists():
        return []
    import json
    with open(qb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Filter for FULL only, return minimal fields
    filtered = [
        {
            "id": q["id"],
            "text": q["text"],
            "category": q["category"],
            "topics": q.get("topics", []),
            "programmes": q.get("programmes", ["bba", "bca", "mba", "mca"]),
            "variants": q.get("programme_variants", {}),
        }
        for q in data
        if q.get("status") == "FULL"
    ]
    _cached_question_bank = filtered
    return filtered


@app.get("/api/question-bank")
async def get_question_bank():
    """Return verified FULL questions from the question bank."""
    return get_full_question_bank()


@app.get("/api/contacts")
async def get_contacts():
    """Return public admissions and department contacts dynamically parsed from knowledge base."""
    from app.contacts import get_contact_directory
    directory = get_contact_directory()
    admissions_entries = directory._services.get("Admissions", [])
    accounts_entries = directory._services.get("Accounts & Payments", [])
    lms_entries = directory._services.get("Learning Management System", [])
    exams_entries = directory._services.get("Examinations", [])

    def format_entries(entries):
        return [
            {"person": e.person, "phone": e.phone, "prog_tag": e.prog_tag}
            for e in entries
        ]

    return {
        "admissions": format_entries(admissions_entries),
        "accounts": format_entries(accounts_entries),
        "lms": format_entries(lms_entries),
        "examinations": format_entries(exams_entries),
        "admissions_line": directory.get_contact_line(topic="admission"),
    }


# -----------------------------------------------------------------------
# /api/me aliases
# -----------------------------------------------------------------------

from app.auth import get_current_user


@app.get("/api/me/export")
async def api_me_export(user: Dict[str, Any] = Depends(get_current_user)):
    from app.routes.auth_routes import export_my_data
    return await export_my_data(user)


@app.delete("/api/me")
async def api_me_delete(user: Dict[str, Any] = Depends(get_current_user)):
    from app.routes.auth_routes import delete_my_account
    return await delete_my_account(user)

