"""FastAPI HTTP server for the CHARUSAT Online Course Assistant + SkillForge AI.

This module provides:
1. The original chatbot HTTP API with session-based conversation history
2. SkillForge AI career mentor endpoints for resume/portfolio analysis
   and personalized career plan generation

Run with::

    python run.py
    # or: uvicorn api:app --reload --port 8000
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure the backend root is on sys.path so ``app.*`` imports work when
# running with ``uvicorn api:app`` from the backend directory.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ensure_directories
from app.conversation_history import ConversationStore
from app.utils import logger, print_info, print_warning

# -----------------------------------------------------------------------
# Application bootstrap — chatbot RAG pipeline (best-effort)
# -----------------------------------------------------------------------

ensure_directories()

# Try to initialise the RAG pipeline. If the vector store isn't ready
# (e.g. first run focused on SkillForge), the chatbot endpoints will
# return a graceful error but SkillForge endpoints will still work.
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

conversation_store = ConversationStore()

# -----------------------------------------------------------------------
# SkillForge AI bootstrap
# -----------------------------------------------------------------------
from app.career_engine import (
    calculate_skill_gap,
    generate_personalized_plan,
    get_available_roles,
    merge_profiles,
)
from app.database import get_db, save_analysis, get_analysis, save_plan, get_plan
from app.portfolio_analyzer import analyze_portfolio
from app.resume_analyzer import analyze_resume
from app.schemas import (
    AnalysisResponse,
    FinalCareerPlan,
    PlanResponse,
    ProfileSource,
    StudentProfile,
)

print_info("[SkillForge] Career AI pipeline initialised.")

# -----------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------

app = FastAPI(
    title="SkillForge AI — Personalized Career Mentor",
    description=(
        "SkillForge AI API providing:\n"
        "- Personalized career mentoring (resume/portfolio analysis, skill gap, roadmap)\n"
        "- CHARUSAT Online Course chatbot (RAG-based Q&A)\n"
    ),
    version="2.0.0",
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
# Chatbot Request / Response models (unchanged)
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
    """Response from ``POST /chat``.

    Only the assistant answer is returned to the client. Debug details
    (retrieved chunks, scores, resolved query, LLM status) are written to the
    backend logs, not exposed in the API payload.
    """
    session_id: str
    answer: str


class ClearHistoryResponse(BaseModel):
    """Response from ``DELETE /chat/history/{session_id}``."""
    session_id: str
    cleared: bool


class HealthResponse(BaseModel):
    """Response from ``GET /health``."""
    status: str
    vector_store_documents: int
    skillforge_ready: bool = True
    gemini_available: bool = False


# -----------------------------------------------------------------------
# Chatbot Endpoints (unchanged)
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
    6. Returns the answer (and session id) to the client; debug details are
       written to the backend logs only.
    """
    if not _rag_ready:
        raise HTTPException(status_code=503, detail="Chatbot RAG pipeline is not available.")

    # 1. Session management
    session_id = conversation_store.get_or_create_session(request.session_id)

    # 2. Get recent history
    history = conversation_store.get_recent_history(session_id)

    # 3-5. Answer with history-aware RAG chain
    try:
        answer_text, _retrieved, _resolved_query = rag_chain.answer_with_history(
            request.question, history,
        )
    except Exception as exc:
        logger.error("RAG chain failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate answer") from exc

    # 6. Persist the turn
    conversation_store.add_message(session_id, "user", request.question)
    conversation_store.add_message(session_id, "assistant", answer_text)

    return ChatResponse(
        session_id=session_id,
        answer=answer_text,
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
        "message": "SkillForge AI — Personalized Career Mentor is running.",
        "docs": "/docs",
        "health": "/health",
        "career_api": "/api/career/roles",
    }


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Simple health check."""
    try:
        count = vector_store._collection.count() if _rag_ready else -1
    except Exception:
        count = -1

    gemini_avail = False
    try:
        from app.gemini_client import get_gemini_client
        gemini_avail = get_gemini_client().is_available
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        vector_store_documents=count,
        skillforge_ready=True,
        gemini_available=gemini_avail,
    )


# =======================================================================
# SkillForge AI Career Endpoints
# =======================================================================


@app.get("/api/career/roles")
async def get_roles():
    """Return the list of supported target career roles."""
    return {"roles": get_available_roles()}


@app.post("/api/career/analyze")
async def career_analyze(
    target_career: str = Form(...),
    portfolio_url: Optional[str] = Form(default=None),
    user_id: Optional[str] = Form(default=None),
    resume: Optional[UploadFile] = File(default=None),
):
    """Analyze resume and/or portfolio for career planning.

    Accepts multipart form data with:
    - target_career (required): The target career role
    - resume (optional): PDF resume file upload
    - portfolio_url (optional): Portfolio or GitHub URL
    - user_id (optional): Client-generated user ID

    At least one of resume or portfolio_url must be provided.

    CRITICAL: This endpoint ONLY uses the inputs provided in THIS request.
    It NEVER reuses previous resume data when only portfolio is provided,
    and vice versa.
    """
    # Validate: at least one input source
    has_resume = resume is not None and resume.filename
    has_portfolio = portfolio_url is not None and portfolio_url.strip()

    if not has_resume and not has_portfolio:
        raise HTTPException(
            status_code=400,
            detail="At least one of resume or portfolio_url must be provided.",
        )

    # Generate user_id if not provided
    if not user_id:
        user_id = str(uuid.uuid4())

    analysis_id = str(uuid.uuid4())

    # Determine input mode
    if has_resume and has_portfolio:
        input_mode = "both"
    elif has_resume:
        input_mode = "resume_only"
    else:
        input_mode = "portfolio_only"

    print_info(f"[SkillForge] Analysis request: mode={input_mode}, role={target_career}, user={user_id[:8]}...")

    # Step 1: Analyze resume (only if provided in THIS request)
    resume_profile = None
    if has_resume:
        try:
            file_bytes = await resume.read()
            resume_profile = analyze_resume(file_bytes)
            if resume_profile:
                print_info(f"[SkillForge] Resume: {len(resume_profile.skills)} skills extracted")
        except Exception as exc:
            logger.error("Resume analysis failed: %s", exc)
            resume_profile = StudentProfile(
                source=ProfileSource.RESUME,
                confidence="low",
                extraction_notes=f"Resume analysis failed: {exc}",
            )

    # Step 2: Analyze portfolio (only if provided in THIS request)
    portfolio_profile = None
    if has_portfolio:
        try:
            portfolio_profile = analyze_portfolio(portfolio_url)
            if portfolio_profile:
                print_info(f"[SkillForge] Portfolio: {len(portfolio_profile.skills)} skills extracted")
        except Exception as exc:
            logger.error("Portfolio analysis failed: %s", exc)
            portfolio_profile = StudentProfile(
                source=ProfileSource.PORTFOLIO,
                confidence="low",
                extraction_notes=f"Portfolio analysis failed: {exc}",
            )

    # Step 3: Merge profiles based on CURRENT input only
    unified_profile = merge_profiles(resume_profile, portfolio_profile)

    # Step 4: Calculate skill gap
    skill_gap = calculate_skill_gap(unified_profile, target_career)

    # Step 5: Build response
    created_at = datetime.now(timezone.utc).isoformat()

    response_data = {
        "analysis_id": analysis_id,
        "user_id": user_id,
        "student_profile": unified_profile.model_dump(),
        "skill_gap": skill_gap.model_dump(),
        "target_role": target_career,
        "input_mode": input_mode,
        "created_at": created_at,
    }

    # Step 6: Save to MongoDB (best-effort)
    save_analysis(response_data)

    return response_data


@app.post("/api/career/plan")
async def career_plan(
    analysis_id: Optional[str] = Form(default=None),
    target_career: str = Form(...),
    portfolio_url: Optional[str] = Form(default=None),
    user_id: Optional[str] = Form(default=None),
    resume: Optional[UploadFile] = File(default=None),
):
    """Generate a personalized career plan.

    Can work in two modes:
    1. With analysis_id: uses a previously saved analysis
    2. Without analysis_id: runs fresh analysis from resume/portfolio

    Returns a complete FinalCareerPlan with roadmap, courses, projects,
    certifications, interview prep, and career advice.
    """
    if not user_id:
        user_id = str(uuid.uuid4())

    plan_id = str(uuid.uuid4())

    # Try to load existing analysis
    analysis_data = None
    if analysis_id:
        analysis_data = get_analysis(analysis_id, user_id)

    if analysis_data:
        # Use existing analysis
        profile = StudentProfile.model_validate(analysis_data["student_profile"])
        from app.schemas import SkillGapAnalysis
        skill_gap = SkillGapAnalysis.model_validate(analysis_data["skill_gap"])
        input_mode = analysis_data.get("input_mode", "resume_only")
        target_career = analysis_data.get("target_role", target_career)
    else:
        # Run fresh analysis
        has_resume = resume is not None and resume.filename
        has_portfolio = portfolio_url is not None and portfolio_url.strip()

        if not has_resume and not has_portfolio:
            raise HTTPException(
                status_code=400,
                detail="Provide analysis_id or at least one of resume/portfolio_url.",
            )

        if has_resume and has_portfolio:
            input_mode = "both"
        elif has_resume:
            input_mode = "resume_only"
        else:
            input_mode = "portfolio_only"

        resume_profile = None
        if has_resume:
            try:
                file_bytes = await resume.read()
                resume_profile = analyze_resume(file_bytes)
            except Exception as exc:
                logger.error("Resume analysis failed: %s", exc)

        portfolio_profile = None
        if has_portfolio:
            try:
                portfolio_profile = analyze_portfolio(portfolio_url)
            except Exception as exc:
                logger.error("Portfolio analysis failed: %s", exc)

        profile = merge_profiles(resume_profile, portfolio_profile)
        skill_gap = calculate_skill_gap(profile, target_career)

    # Generate personalized plan
    print_info(f"[SkillForge] Generating plan for {target_career}...")
    career_plan = generate_personalized_plan(profile, skill_gap, target_career, input_mode)

    created_at = datetime.now(timezone.utc).isoformat()

    response_data = {
        "plan_id": plan_id,
        "user_id": user_id,
        "career_plan": career_plan.model_dump(),
        "created_at": created_at,
    }

    # Save to MongoDB
    save_plan(response_data)

    return response_data


@app.get("/api/career/analysis/{analysis_id}")
async def get_career_analysis(analysis_id: str, user_id: str):
    """Retrieve a saved analysis by ID."""
    data = get_analysis(analysis_id, user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return data


@app.get("/api/career/plan/{plan_id}")
async def get_career_plan(plan_id: str, user_id: str):
    """Retrieve a saved plan by ID."""
    data = get_plan(plan_id, user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return data

