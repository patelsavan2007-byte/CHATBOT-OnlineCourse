"""Enhanced chat API route with conversation persistence.

This route wraps the existing RAG pipeline to add:
  - Conversation creation/association for authenticated users
  - Message persistence (user + assistant) in MongoDB
  - Guest mode support (no persistence, message count tracking)
  - Guest conversation migration on signup/login
  - Context-aware suggested follow-up questions
  - Streaming responses with typing indicator

The existing ``POST /chat`` endpoint in api.py is kept unchanged for
backward compatibility.

Endpoints:
  POST /api/chat         ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ send a message (guest or authenticated)
  POST /api/chat/stream  ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ send a message with streaming response
  POST /api/chat/migrate ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ migrate guest conversation to authenticated user
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import get_optional_user, get_current_user
from app.database import get_db
from app.models import (
    add_message_feedback,
    add_user_correction,
    create_conversation,
    create_message,
    generate_conversation_title,
    get_conversation,
    get_conversation_messages,
    get_feedback_stats,
    update_conversation,
)
from app.utils import logger

router = APIRouter(prefix="/api/chat", tags=["chat"])


from app.smalltalk import is_smalltalk, converse
from app.suggestions import generate_suggestions


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatMessageRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    use_cache: Optional[bool] = True


class ChatMessageResponse(BaseModel):
    answer: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    suggested_questions: Optional[List[str]] = None
    quick_replies: Optional[List[str]] = None


class StreamChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None


class FeedbackRequest(BaseModel):
    message_id: str = Field(..., description="Message ID to add feedback to")
    feedback: str = Field(..., description="Feedback type: 'thumbs_up' or 'thumbs_down'")


class UserCorrectionRequest(BaseModel):
    message_id: str = Field(..., description="Message ID to add correction to")
    correction: str = Field(..., description="User's corrected answer")


class MigrateConversationRequest(BaseModel):
    """Migrate a guest conversation to the authenticated user account."""
    messages: List[Dict[str, Any]] = Field(
        ...,
        description="List of {role, content} message objects from the guest session",
    )
    title: Optional[str] = None


class MigrateConversationResponse(BaseModel):
    conversation_id: str
    message_count: int


# ---------------------------------------------------------------------------
# RAG pipeline access (lazy import to avoid circular dependencies)
# ---------------------------------------------------------------------------

def _get_rag_chain():
    """Get the RAG chain from the main api module.

    The RAG pipeline is initialized in api.py. We access it through the
    module-level variables set during startup.
    """
    import sys
    api_module = sys.modules.get("api")
    if api_module is None:
        return None, False

    rag_ready = getattr(api_module, "_rag_ready", False)
    rag_chain = getattr(api_module, "rag_chain", None)
    return rag_chain, rag_ready


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _persist_turn(
    db,
    user: Optional[Dict[str, Any]],
    conversation_id: Optional[str],
    question: str,
    assistant_answer: str,
    user_id: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    suggested: Optional[List[str]] = None,
) -> tuple:
    """Save user + assistant messages; returns the assistant message and conversation_id."""
    if db is None or user is None:
        return None, conversation_id

    actual_user_id = user_id or user["id"]

    if not conversation_id:
        title = generate_conversation_title(question)
        conv = create_conversation(db, user_id=actual_user_id, title=title)
        conversation_id = conv["id"]

    create_message(
        db,
        conversation_id=conversation_id,
        role="user",
        content=question,
    )
    assistant_msg = create_message(
        db,
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_answer,
        sources=sources or [],
        suggested_questions=suggested or [],
    )
    return assistant_msg, conversation_id


def _resolve_history(
    request_history: Optional[List[Dict[str, Any]]],
    user: Optional[Dict[str, Any]],
    conversation_id: Optional[str],
) -> Optional[List[Dict[str, Any]]]:
    """Resolve conversation history from request or database."""
    if request_history:
        return request_history
    if user is not None and conversation_id:
        db = get_db()
        if db is not None:
            recent = get_conversation_messages(db, conversation_id)
            if recent:
                return recent[-20:]
    return None


def _extract_sources(retrieved: List[Any]) -> List[Dict[str, Any]]:
    """Extract and deduplicate sources (PDF and markdown web pages) from retrieved chunks."""
    sources = []
    seen = set()
    if retrieved:
        for doc, score in retrieved:
            meta = doc.metadata
            source_path = str(meta.get("source", ""))
            page = meta.get("page")
            url = meta.get("url")
            key = (source_path, page or url or meta.get("chunk_id"))
            if key in seen:
                continue
            seen.add(key)
            src_item: Dict[str, Any] = {
                "source": source_path,
                "page": page,
                "program": meta.get("program_name"),
                "score": round(score, 3),
            }
            if url:
                src_item["url"] = url
            sources.append(src_item)
    return sources


@dataclass
class _TurnOutcome:
    answer: str
    sources: List[Dict[str, Any]]
    rag_result: Optional[Any]
    plan: Any
    kind: str  # "answer" | "smalltalk" | "unrelated"


def _process_chat_turn(
    question: str,
    history: Optional[List[Dict[str, Any]]],
    rag_chain: Any,
    use_cache: Optional[bool] = True,
) -> _TurnOutcome:
    """Execute a single chat turn through RAG and build answer and sources.
    Shared by both /api/chat and /api/chat/stream.
    """
    from app.smalltalk import is_smalltalk, converse
    from app.conversation import analyze_turn

    ql = (question or "").lower()
    plan = analyze_turn(question, history=history)

    # 1. Fast path for smalltalk / conversational pleasantries / out-of-scope
    if is_smalltalk(question):
        llm_client = getattr(rag_chain, "llm_client", None)
        answer_text = converse(question, history=history, llm_client=llm_client)
        return _TurnOutcome(answer_text, [], None, plan, "smalltalk")

    # 2. Execute RAG
    res = rag_chain.answer(question, history=history, use_cache=use_cache)
    answer_text = res.answer or ""
    retrieved = res.retrieved
    effective_plan = getattr(res, "plan", None) or plan

    import re
    ql2 = (question or "").lower()
    try:
        from app import session_state
        conv_id = None
        conv_id = getattr(res, "conversation_id", None) if 'res' in locals() else None
        if not conv_id and effective_plan:
            conv_id = getattr(effective_plan, "conversation_id", None)
        st = session_state.get_state(conv_id) if conv_id else {}
    except Exception:
        conv_id = None
        st = {}
    degree_q2 = bool(re.search(r'\b(what\s+degree|which\s+degree|degree\s+will\s+i\s+get|provisional\s+certificate|sample\s+certificate|show\s+degree\s+certificate|show\s+the\s+sample\s+certificate)\b', ql2))
    ugc_q = bool(re.search(r'\b(ugc|recognized|recognised)\b', ql2))
    aff = bool(re.match(r'^\s*(yes|yeah|yep|sure|ok|okay|show|show\s+me|haan|haann?|please)\s*[\.!\?]*\s*$', ql2) or re.search(r'\b(yes|yeah|yep|sure|okay|ok|show\s+me|please|haan|haann?)\b', ql2))
    explicit_show = bool(re.search(r'\b(show\s+the\s+sample\s+certificate|show\s+degree\s+certificate\s+sample|show\s+sample\s+certificate)\b', ql2))
    pending_offer = (st.get("pendingOffer") == "degree_sample") if conv_id else False
    if explicit_show and not aff:
        aff = True
    if degree_q2 and not ugc_q and not aff and not pending_offer and "want to see" not in answer_text.lower():
        answer_text = (answer_text.rstrip() + "\n\nWant to see a sample certificate?").strip()
        try:
            if conv_id:
                from app import session_state
                session_state.update_state(conv_id, pendingOffer="degree_sample")
        except Exception:
            pass
    elif (aff and pending_offer) and not ugc_q:
        imgs = "\n\n![BCA Front Sample](https://charusat.online/images/BCA-Front.webp)\n\n![BCA Back Sample](https://charusat.online/images/BCA-Back%20web.webp)"
        answer_text = (imgs.strip() + "\n\n**BCA Degree Certificate - Sample (Front and Back)**").strip()
        try:
            if conv_id:
                from app import session_state
                session_state.clear_state(conv_id)
        except Exception:
            pass
    elif explicit_show and "BCA-Front" not in answer_text:
        imgs = "\n\n![BCA Front Sample](https://charusat.online/images/BCA-Front.webp)\n\n![BCA Back Sample](https://charusat.online/images/BCA-Back%20web.webp)"
        answer_text = (imgs.strip() + "\n\n**BCA Degree Certificate - Sample (Front and Back)**").strip()
        try:
            if conv_id:
                from app import session_state
                session_state.clear_state(conv_id)
        except Exception:
            pass

    # 3. If RAG returned no chunks and query is not course-specific, use conversational fallback
    if not retrieved and effective_plan.topic == "general" and not effective_plan.programmes:
        llm_client = getattr(rag_chain, "llm_client", None)
        answer_text = converse(question, history=history, llm_client=llm_client)
        import re
        ql2 = (question or "").lower()
        try:
            from app import session_state
            conv_id = getattr(res, "conversation_id", None)
            st = session_state.get_state(conv_id) if conv_id else {}
        except Exception:
            conv_id = None
            st = {}
        degree_q2 = bool(re.search(r'\b(what\s+degree|which\s+degree|degree\s+will\s+i\s+get|sample\s+certificate|show\s+degree\s+certificate|show\s+the\s+sample\s+certificate)\b', ql2))
        ugc_q = bool(re.search(r'\b(ugc|recognized|recognised)\b', ql2))
        aff = bool(re.match(r'^\s*(yes|yeah|yep|sure|ok|okay|show|show\s+me|haan|haann?|please)\s*[\.!\?]*\s*$', ql2) or re.search(r'\b(yes|yeah|yep|sure|okay|ok|show\s+me|please|haan|haann?)\b', ql2))
        explicit_show = bool(re.search(r'\b(show\s+the\s+sample\s+certificate|show\s+degree\s+certificate\s+sample|show\s+sample\s+certificate)\b', ql2))
        if explicit_show and not aff:
            aff = True
        pending_offer = (st.get("pendingOffer") == "degree_sample") if conv_id else False
        if degree_q2 and not ugc_q and not aff and not pending_offer and "want to see" not in answer_text.lower():
            answer_text = (answer_text.rstrip() + "\n\nWant to see a sample certificate?").strip()
            try:
                if conv_id:
                    from app import session_state
                    session_state.update_state(conv_id, pendingOffer="degree_sample")
            except Exception:
                pass
        elif (aff and pending_offer) and not ugc_q:
            imgs = "\n\n![BCA Front Sample](https://charusat.online/images/BCA-Front.webp)\n\n![BCA Back Sample](https://charusat.online/images/BCA-Back%20web.webp)"
            answer_text = (imgs.strip() + "\n\n**BCA Degree Certificate - Sample (Front and Back)**").strip()
            try:
                if conv_id:
                    from app import session_state
                    session_state.clear_state(conv_id)
            except Exception:
                pass
        elif explicit_show and "BCA-Front" not in answer_text:
            imgs = "\n\n![BCA Front Sample](https://charusat.online/images/BCA-Front.webp)\n\n![BCA Back Sample](https://charusat.online/images/BCA-Back%20web.webp)"
            answer_text = (imgs.strip() + "\n\n**BCA Degree Certificate - Sample (Front and Back)**").strip()
            try:
                if conv_id:
                    from app import session_state
                    session_state.clear_state(conv_id)
            except Exception:
                pass
        return _TurnOutcome(answer_text, [], res, effective_plan, "unrelated")

    from app.citations import extract_citations
    sources = extract_citations(retrieved, answer_text=answer_text)
    return _TurnOutcome(answer_text, sources, res, effective_plan, "answer")


def _generate_suggested_questions(
    outcome: _TurnOutcome,
    history: Optional[List[Dict[str, Any]]],
    max_suggestions: int = 3,
) -> List[str]:
    """Return deterministic, journey-aware suggestions from the question bank.

    Suggestions are never generated by the LLM, so they cannot invent a
    programme, fee, or URL. Greetings, farewells and unrelated chatter get
    none; not-found answers get related answerable questions instead.
    """
    if outcome.kind in ("smalltalk", "unrelated"):
        return []
    if "vague_clarification" in str(getattr(outcome.rag_result, "status", "")):
        return []
    try:
        suggestions = generate_suggestions(
            outcome.plan,
            outcome.answer,
            history=history,
            is_smalltalk=False,
            is_unrelated=False,
        )
        return suggestions[:max_suggestions]
    except Exception as exc:
        logger.warning("Failed to generate suggested questions: %s", exc)
        return []


def _quick_replies(outcome: _TurnOutcome) -> List[str]:
    """Programme quick replies for the vague-question clarification state."""
    status = str(getattr(outcome.rag_result, "status", "") or "")
    if "vague_clarification" in status:
        return ["Online BBA", "Online BCA", "Online MBA", "Online MCA"]
    return []


def _thinking_status(plan: Any) -> str:
    """Natural, topic-aware status shown before the first answer token."""
    topic = getattr(plan, "topic", "general")
    statuses = {
        "fees": "Checking the fee detailsÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¦",
        "subjects": "Looking through the curriculumÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¦",
        "eligibility": "Checking the eligibility criteriaÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¦",
        "admission": "Reviewing the admission processÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¦",
        "duration": "Checking the programme structureÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¦",
        "grading": "Reviewing the examination and grading rulesÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¦",
        "lms": "Checking the LMS guidanceÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¦",
        "contact": "Finding the right support contactÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¦",
        "career": "Checking career and placement detailsÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¦",
        "refund": "Reviewing the refund policyÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¦",
    }
    return statuses.get(topic, "Looking that up...")
    if db is None:
        return
    try:
        from app.conversation import analyze_turn
        plan = getattr(rag_result, "plan", None) or analyze_turn(question, history=None)
        status_val = getattr(rag_result, "status", getattr(rag_chain, "last_status", "unknown")) if (rag_result or rag_chain) else "unknown"
        status_str = str(status_val).lower()
        is_gap = (
            "not_found" in status_str
            or "missing" in status_str
            or "no_content" in status_str
            or "fallback" in status_str
            or "couldn't find" in answer.lower()
        )
        timing_dict = getattr(rag_result, "timing", {}) if rag_result else getattr(rag_chain, "last_timing", {})
        latency = timing_dict.get("total_s", 0.0) if timing_dict else 0.0

        event = {
            "timestamp": datetime.now(timezone.utc),
            "question": question,
            "answer_preview": (answer[:250] + "...") if len(answer) > 250 else answer,
            "status": str(status_val),
            "programmes": getattr(plan, "programmes", []),
            "topic": getattr(plan, "topic", "general"),
            "year": getattr(plan, "year", None),
            "user_id": user.get("id") if user else None,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "latency_s": round(latency, 3),
            "is_gap": is_gap,
            "feedback": None,
        }
        db.chat_events.insert_one(event)
    except Exception as exc:
        logger.warning("Failed to log chat event: %s", exc)


@router.post("", response_model=ChatMessageResponse)
async def chat_message(
    request: ChatMessageRequest,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    """Send a chat message.

    For authenticated users: creates/uses a conversation, persists messages.
    For guests: just calls RAG pipeline, no persistence.
    """
    conversation_id = request.conversation_id
    rag_chain, rag_ready = _get_rag_chain()

    if not rag_ready or rag_chain is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chatbot RAG pipeline is not available.",
        )

    # Conversation context for retrieval
    history = _resolve_history(request.history, user, conversation_id)

    # Call the shared RAG turn processing
    try:
        outcome = _process_chat_turn(
            request.question, history, rag_chain, use_cache=request.use_cache
        )
    except Exception as exc:
        logger.error("RAG chain failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate answer",
        ) from exc

    answer_text = outcome.answer
    sources = outcome.sources
    rag_result = outcome.rag_result
    suggested = _generate_suggested_questions(outcome, history)
    quick_replies = _quick_replies(outcome)
    db = get_db()

    # For guests, return without persistence (but log event)
    if user is None:
        _log_chat_event(db, request.question, answer_text, user=None, rag_result=rag_result)
        return ChatMessageResponse(
            answer=answer_text,
            suggested_questions=suggested,
            quick_replies=quick_replies,
        )

    # For authenticated users, persist to MongoDB
    if db is None:
        # MongoDB unavailable ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ return answer without persistence
        return ChatMessageResponse(
            answer=answer_text,
            suggested_questions=suggested,
            quick_replies=quick_replies,
        )

    # Create new conversation if needed
    if not conversation_id:
        title = generate_conversation_title(request.question)
        conv = create_conversation(db, user_id=user["id"], title=title)
        conversation_id = conv["id"]
    else:
        # Verify conversation belongs to user
        conv = get_conversation(db, conversation_id, user["id"])
        if not conv:
            # Create a new one instead of failing
            title = generate_conversation_title(request.question)
            conv = create_conversation(db, user_id=user["id"], title=title)
            conversation_id = conv["id"]

    # Save user message
    create_message(
        db,
        conversation_id=conversation_id,
        role="user",
        content=request.question,
    )

    # Save assistant response
    assistant_msg = create_message(
        db,
        conversation_id=conversation_id,
        role="assistant",
        content=answer_text,
        sources=sources,
        suggested_questions=suggested,
    )

    _log_chat_event(
        db,
        request.question,
        answer_text,
        user=user,
        conversation_id=conversation_id,
        message_id=assistant_msg["id"],
        rag_result=rag_result,
    )

    return ChatMessageResponse(
        answer=answer_text,
        conversation_id=conversation_id,
        message_id=assistant_msg["id"],
        suggested_questions=suggested,
        quick_replies=quick_replies,
    )


@router.post("/stream")
async def chat_message_stream(
    request: StreamChatRequest,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    """Send a chat message with streaming response.

    Returns a Server-Sent Events (SSE) stream with:
    - typing indicator events
    - answer chunks as they are generated
    """
    conversation_id = request.conversation_id
    rag_chain, rag_ready = _get_rag_chain()

    if not rag_ready or rag_chain is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chatbot RAG pipeline is not available.",
        )

    history = _resolve_history(request.history, user, conversation_id)

    async def generate_response():
        from app.conversation import analyze_turn
        from app.smalltalk import is_smalltalk
        import uuid
        qid = str(uuid.uuid4())
        try:
            from app import llm_call_counter
            llm_call_counter.reset(qid)
        except Exception:
            pass
        try:
            if hasattr(rag_chain, "llm_client"):
                rag_chain.llm_client._last_qid = qid
        except Exception:
            pass

        plan = analyze_turn(request.question, history=history)
        kind = "smalltalk" if is_smalltalk(request.question) else None

        if kind == "smalltalk" or (hasattr(plan, "is_clarification") and plan.is_clarification):
            try:
                outcome = await asyncio.to_thread(
                    _process_chat_turn, request.question, history, rag_chain, True
                )
            except Exception as exc:
                logger.error("Streaming RAG chain failed: %s", exc)
                yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to generate answer'})}\n\n"
                return
            answer_text = outcome.answer
            sources = outcome.sources
            suggested = _generate_suggested_questions(outcome, history)
            quick_replies = _quick_replies(outcome)
            try:
                from app import llm_call_counter
                _llm_calls = llm_call_counter.get_calls(qid)
            except Exception:
                _llm_calls = 0
            # smalltalk/cached-like: can chunk quickly
            chunk_size = 18
            for i in range(0, len(answer_text), chunk_size):
                chunk = answer_text[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            db = get_db()
            assistant_msg, conv_id = _persist_turn(
                db,
                user,
                conversation_id,
                request.question,
                answer_text,
                sources=sources,
                suggested=suggested,
            )
            _log_chat_event(
                db,
                request.question,
                answer_text,
                user=user,
                conversation_id=conv_id,
                message_id=assistant_msg["id"] if assistant_msg else None,
                rag_result=outcome.rag_result,
            )
            try:
                from app import llm_call_counter
                _llm_calls = llm_call_counter.get_calls(qid)
            except Exception:
                _llm_calls = 0
            final_data = {
                "type": "done",
                "answer": answer_text,
                "conversation_id": conv_id,
                "message_id": assistant_msg["id"] if assistant_msg else None,
                "suggested_questions": suggested,
                "quick_replies": quick_replies,
                "llm_calls": _llm_calls,
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            return

        import random
        status_msgs = [
            _thinking_status(plan),
            "Gathering relevant details...",
            "Searching for accurate information...",
            "Reviewing the available details...",
        ]
        yield f"data: {json.dumps({'type': 'typing', 'status': 'searching', 'message': random.choice(status_msgs)})}\n\n"

        try:
            outcome = await asyncio.to_thread(
                _process_chat_turn, request.question, history, rag_chain, True
            )
        except Exception as exc:
            logger.error("Streaming RAG chain failed: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to generate answer'})}\n\n"
            return

        answer_text = outcome.answer
        sources = outcome.sources
        suggested = _generate_suggested_questions(outcome, history)
        quick_replies = _quick_replies(outcome)

        # Use single grounded answer only (no second LLM call)
        chunk_size = 18
        for i in range(0, len(answer_text), chunk_size):
            chunk = answer_text[i:i + chunk_size]
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        db = get_db()
        assistant_msg, conv_id = _persist_turn(
            db,
            user,
            conversation_id,
            request.question,
            answer_text,
            sources=sources,
            suggested=suggested,
        )
        _log_chat_event(
            db,
            request.question,
            answer_text,
            user=user,
            conversation_id=conv_id,
            message_id=assistant_msg["id"] if assistant_msg else None,
            rag_result=outcome.rag_result,
        )
        try:
            from app import llm_call_counter
            _llm_calls = llm_call_counter.get_calls(qid)
        except Exception:
            _llm_calls = 0
        final_data = {
            "type": "done",
            "answer": answer_text,
            "conversation_id": conversation_id,
            "message_id": assistant_msg["id"] if "assistant_msg" in locals() else None,
            "suggested_questions": suggested,
            "quick_replies": quick_replies,
            "llm_calls": _llm_calls,
        }
        yield f"data: {json.dumps(final_data)}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )




@router.post("/migrate", response_model=MigrateConversationResponse)
async def migrate_guest_conversation(
    request: MigrateConversationRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Migrate a guest conversation to the authenticated user account.

    Called after a guest user signs up or logs in. The guest local
    messages are saved as a new conversation owned by the user.
    """
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    if not request.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages to migrate",
        )

    # Generate title from first user message
    first_user_msg = next(
        (m for m in request.messages if m.get("role") == "user"),
        None,
    )
    title = request.title or (
        generate_conversation_title(first_user_msg["content"])
        if first_user_msg and first_user_msg.get("content")
        else "Migrated Chat"
    )

    # Create conversation
    conv = create_conversation(db, user_id=user["id"], title=title)

    # Save all messages
    count = 0
    for msg in request.messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            continue
        create_message(
            db,
            conversation_id=conv["id"],
            role=role,
            content=content,
            sources=msg.get("sources", []),
        )
        count += 1

    logger.info(
        "Migrated guest conversation: user_id=%s, conversation_id=%s, messages=%d",
        user["id"], conv["id"], count,
    )

    return MigrateConversationResponse(
        conversation_id=conv["id"],
        message_count=count,
    )


@router.post("/feedback")
async def add_feedback(
    request: FeedbackRequest,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    """Add feedback (thumbs up/down) to a message.

    Args:
        request: Feedback request with message_id and feedback type
        user: Optional authenticated user

    Returns:
        Updated message with feedback
    """
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    if request.feedback not in ("thumbs_up", "thumbs_down"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feedback type. Must be 'thumbs_up' or 'thumbs_down'",
        )

    updated_message = add_message_feedback(db, request.message_id, request.feedback)
    if updated_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    try:
        db.chat_events.update_one(
            {"message_id": request.message_id},
            {"$set": {"feedback": request.feedback}},
        )
    except Exception:
        pass

    return {"status": "success", "message": "Feedback added successfully", "updated_message": updated_message}


@router.post("/correction")
async def add_correction(
    request: UserCorrectionRequest,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    """Add user correction to a message.

    Args:
        request: Correction request with message_id and corrected answer
        user: Optional authenticated user

    Returns:
        Updated message with correction
    """
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    updated_message = add_user_correction(db, request.message_id, request.correction)
    if updated_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    return {"message": "Correction added successfully", "message": updated_message}


@router.get("/feedback/stats")
async def feedback_stats(
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    """Get feedback statistics.

    Args:
        user: Optional authenticated user (if provided, stats are filtered by user)

    Returns:
        Feedback statistics
    """
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    user_id = user["id"] if user else None
    stats = get_feedback_stats(db, user_id)
    return stats


