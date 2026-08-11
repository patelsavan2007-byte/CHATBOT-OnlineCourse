"""FastAPI HTTP server for the CHARUSAT Online Course Assistant.

This module provides the HTTP API for the chatbot with session-based
conversation history.  It is a **separate entry point** from the CLI
(``main.py``); both share the same RAG pipeline, LLM client, and retriever.

Run with::

    uvicorn api:app --reload --port 8000

**Important notes:**

* Conversation history is stored **in-memory only**.  Restarting this server
  clears all session data.
* There is **no authentication**.  The ``session_id`` is the sole conversation
  identifier — there are no user accounts, logins, or tokens.
* There is **no database** backing the session store.  A persistence layer can
  be added later without changing the API contract.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure the backend root is on sys.path so ``app.*`` imports work when
# running with ``uvicorn api:app`` from the backend directory.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import config
from app.config import ensure_directories
from app.conversation_history import ConversationStore
from app.embeddings import EmbeddingStore
from app.llm import LLMClient
from app.rag_chain import RAGChain
from app.retriever import RAGRetriever
from app.utils import logger, print_info, print_warning


# -----------------------------------------------------------------------
# Application bootstrap
# -----------------------------------------------------------------------

ensure_directories()

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
        print_warning(f"Failed to build vector store: {build_exc}")
        raise SystemExit(1) from build_exc

retriever = RAGRetriever(vector_store)
llm_client = LLMClient()
rag_chain = RAGChain(retriever, llm_client)
conversation_store = ConversationStore()

# -----------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------

app = FastAPI(
    title="CHARUSAT Online Course Assistant API",
    description=(
        "HTTP API for the CHARUSAT Online Course chatbot with session-based "
        "conversation history.  History is in-memory only and is lost when "
        "the server restarts.  There is no authentication."
    ),
    version="1.0.0",
)

# Allow CORS for local frontend development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------
# Request / Response models
# -----------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Body for ``POST /chat``."""
    session_id: Optional[str] = Field(
        default=None,
        description=(
            "UUID of an existing conversation session.  If omitted or null, "
            "a new session is created automatically."
        ),
    )
    question: str = Field(
        ...,
        min_length=1,
        description="The user's question.",
    )


class ChatResponse(BaseModel):
    """Response from ``POST /chat``."""
    session_id: str
    answer: str
    sources: List[str]
    resolved_query: str = Field(
        description=(
            "The standalone version of the question used for RAG retrieval.  "
            "May differ from the original question when the user asked a "
            "follow-up that was reformulated using conversation context."
        ),
    )
    llm_status: str = Field(
        description="Which generation backend produced the answer (gemini, groq, fallback, ...).",
    )


class ClearHistoryResponse(BaseModel):
    """Response from ``DELETE /chat/history/{session_id}``."""
    session_id: str
    cleared: bool


class HealthResponse(BaseModel):
    """Response from ``GET /health``."""
    status: str
    vector_store_documents: int


# -----------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Ask a question, optionally continuing an existing conversation.

    If ``session_id`` is omitted, a new session is created and its UUID is
    returned so the client can reuse it for subsequent messages.

    The backend:

    1. Loads conversation history for the session.
    2. Resolves follow-up questions into standalone queries.
    3. Runs the existing RAG retrieval pipeline (unchanged).
    4. Sends history + RAG context + question to the LLM.
    5. Appends the user question and assistant answer to the session.
    6. Returns the answer with sources and the resolved query.
    """
    # 1. Session management
    session_id = conversation_store.get_or_create_session(request.session_id)

    # 2. Get recent history
    history = conversation_store.get_recent_history(session_id)

    # 3-5. Answer with history-aware RAG chain
    try:
        answer_text, retrieved, resolved_query = rag_chain.answer_with_history(
            request.question, history,
        )
    except Exception as exc:
        logger.error("RAG chain failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate answer") from exc

    # 6. Persist the turn
    conversation_store.add_message(session_id, "user", request.question)
    conversation_store.add_message(session_id, "assistant", answer_text)

    # Build source list:
    # 1. If information was NOT found in the knowledge base, do NOT list sources.
    # 2. Otherwise, only list sources for chunks meeting the MIN_SOURCE_SCORE threshold.
    is_not_found = any(
        phrase in answer_text.lower()
        for phrase in ("couldn't find", "could not find", "not present in the context")
    )
    if is_not_found or not retrieved:
        sources = []
    else:
        min_src_score = getattr(config, "MIN_SOURCE_SCORE", 0.60)
        filtered_docs = [
            doc for doc, score in retrieved
            if score >= min_src_score
        ]
        # Fallback to top document if all scores were slightly below threshold but answer was generated
        if not filtered_docs and retrieved:
            filtered_docs = [retrieved[0][0]]

        sources = sorted({
            f"{doc.metadata.get('source', 'unknown')}"
            + (f" (Page {doc.metadata.get('page')})" if doc.metadata.get("page") is not None and str(doc.metadata.get("page")).strip() != "" else "")
            for doc in filtered_docs
        })

    return ChatResponse(
        session_id=session_id,
        answer=answer_text,
        sources=sources,
        resolved_query=resolved_query,
        llm_status=rag_chain.last_status,
    )



@app.delete("/chat/history/{session_id}", response_model=ClearHistoryResponse)
async def clear_history(session_id: str) -> ClearHistoryResponse:
    """Clear all conversation history for a session.

    After clearing, the session still exists but contains no messages.
    Subsequent questions in the same session will behave as if the
    conversation just started.
    """
    cleared = conversation_store.clear_session(session_id)
    if not cleared:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found",
        )
    return ClearHistoryResponse(session_id=session_id, cleared=True)


@app.get("/")
async def root():
    """Root endpoint welcoming users and pointing to docs."""
    return {
        "message": "CHARUSAT Online Course Assistant API is running.",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Simple health check."""
    try:
        count = vector_store._collection.count()
    except Exception:
        count = -1
    return HealthResponse(status="ok", vector_store_documents=count)

