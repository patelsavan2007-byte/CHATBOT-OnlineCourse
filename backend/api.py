"""FastAPI HTTP server for the CHARUSAT Online Course Assistant.

This module provides the chatbot HTTP API for the RAG-based Q&A assistant.

Run with::

    uvicorn api:app --reload --port 8000
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure the backend root is on sys.path so ``app.*`` imports work when
# running with ``uvicorn api:app`` from the backend directory.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
except Exception as rag_exc:
    print_warning(f"RAG pipeline init failed: {rag_exc}. Chatbot will be unavailable.")

# -----------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------

app = FastAPI(
    title="CHARUSAT Online Course Assistant",
    description=(
        "CHARUSAT Online Course Assistant API:\n"
        "- RAG-based Q&A chatbot for CHARUSAT online degree programmes "
        "(fees, eligibility, duration, curriculum, admissions and more)\n"
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
# Chatbot Request / Response models
# -----------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Body for ``POST /chat``."""
    question: str = Field(
        ...,
        min_length=1,
        description="The user's question.",
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


# -----------------------------------------------------------------------
# Chatbot Endpoints
# -----------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Ask a question and return the assistant's answer."""
    logger.info("[CHAT] User query received: question=%r", request.question)

    if not _rag_ready:
        raise HTTPException(status_code=503, detail="Chatbot RAG pipeline is not available.")

    try:
        answer_text, _retrieved = rag_chain.answer(request.question)
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

    return HealthResponse(
        status="ok",
        vector_store_documents=count,
    )
