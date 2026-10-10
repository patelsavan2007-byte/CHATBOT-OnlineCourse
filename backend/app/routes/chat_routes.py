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
  POST /api/chat         — send a message (guest or authenticated)
  POST /api/chat/stream  — send a message with streaming response
  POST /api/chat/migrate — migrate guest conversation to authenticated user
"""
from __future__ import annotations

import asyncio
import json
import os
import re
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


from app.suggestions import generate_suggestions
from app.smalltalk import is_smalltalk, converse



# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatMessageRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None


class ChatMessageResponse(BaseModel):
    answer: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    sources: List[Dict[str, Any]] = []
    suggested_questions: List[str] = []


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
    """Migrate a guest conversation to the authenticated user's account."""
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
    assmt_suggestions: List[str],
    user_id: Optional[str] = None,
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
        sources=[],
        suggested_questions=assmt_suggestions,
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
                return recent[-8:]
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


def _process_chat_turn(
    question: str,
    history: Optional[List[Dict[str, Any]]],
    rag_chain: Any,
) -> Tuple[str, List[Dict[str, Any]], List[str]]:
    """Execute a single chat turn through RAG and build answer, sources, and suggestions.
    Shared by both /api/chat and /api/chat/stream.
    """
    from app.smalltalk import is_smalltalk, converse
    from app.conversation import analyze_turn

    plan = analyze_turn(question, history=history)

    # 1. Fast path for smalltalk / conversational pleasantries / out-of-scope
    if is_smalltalk(question):
        llm_client = getattr(rag_chain, "llm_client", None)
        answer_text = converse(question, history=history, llm_client=llm_client)
        suggestions = generate_suggestions(plan=plan, answer=answer_text, history=history, is_smalltalk=True)
        return answer_text, [], suggestions

    # 2. Execute RAG
    answer_text, retrieved = rag_chain.answer(question, history=history)

    # 3. If RAG returned no chunks and query is not course-specific, use conversational fallback
    if not retrieved and plan.topic == "general" and not plan.programmes:
        llm_client = getattr(rag_chain, "llm_client", None)
        answer_text = converse(question, history=history, llm_client=llm_client)
        return answer_text, [], []

    from app.citations import extract_citations
    sources = extract_citations(retrieved, answer_text=answer_text)
    suggestions = generate_suggestions(
        plan=plan,
        answer=answer_text,
        history=history,
        is_smalltalk=False,
        is_unrelated=False,
    )
    return answer_text, sources, suggestions



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

    # Conversation context for retrieval and suggestions
    history = _resolve_history(request.history, user, conversation_id)

    # Call the shared RAG turn processing
    try:
        answer_text, sources, suggestions = _process_chat_turn(request.question, history, rag_chain)
    except Exception as exc:
        logger.error("RAG chain failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate answer",
        ) from exc

    # For guests, return without persistence
    if user is None:
        return ChatMessageResponse(
            answer=answer_text,
            sources=sources,
            suggested_questions=suggestions,
        )

    # For authenticated users, persist to MongoDB
    db = get_db()
    if db is None:
        # MongoDB unavailable — return answer without persistence
        return ChatMessageResponse(
            answer=answer_text,
            sources=sources,
            suggested_questions=suggestions,
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
        suggested_questions=suggestions,
    )

    return ChatMessageResponse(
        answer=answer_text,
        conversation_id=conversation_id,
        message_id=assistant_msg["id"],
        sources=sources,
        suggested_questions=suggestions,
    )


@router.post("/stream")
async def chat_message_stream(
    request: StreamChatRequest,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    """Send a chat message with streaming response.

    Returns a Server-Sent Events (SSE) stream with:
    - typing indicator events
    - answer chunks as they're generated
    - final sources and suggestions
    """
    conversation_id = request.conversation_id
    rag_chain, rag_ready = _get_rag_chain()

    if not rag_ready or rag_chain is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chatbot RAG pipeline is not available.",
        )

    history = _resolve_history(request.history, user, conversation_id)
    answer_text, sources, suggestions = _process_chat_turn(request.question, history, rag_chain)

    async def generate_response():
        yield f"data: {json.dumps({'type': 'typing', 'status': 'started'})}\n\n"
        await asyncio.sleep(0.05)

        chunk_size = 20
        for i in range(0, len(answer_text), chunk_size):
            chunk = answer_text[i:i + chunk_size]
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            await asyncio.sleep(0.015)

        db = get_db()
        assistant_msg, conv_id = _persist_turn(db, user, conversation_id, request.question, answer_text, suggestions)

        final_data = {
            "type": "done",
            "answer": answer_text,
            "conversation_id": conv_id,
            "message_id": assistant_msg["id"] if assistant_msg else None,
            "sources": sources,
            "suggested_questions": suggestions,
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
    """Migrate a guest conversation to the authenticated user's account.

    Called after a guest user signs up or logs in. The guest's local
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

    return {"message": "Feedback added successfully", "message": updated_message}


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
