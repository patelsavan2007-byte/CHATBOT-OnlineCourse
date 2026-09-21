"""Conversation CRUD API routes.

All endpoints require authentication and are scoped to the current user.

Endpoints:
  GET    /api/conversations            — list user's conversations
  POST   /api/conversations            — create a new conversation
  GET    /api/conversations/{id}       — get conversation with messages
  PATCH  /api/conversations/{id}       — rename conversation
  DELETE /api/conversations/{id}       — delete conversation and its messages
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    create_conversation,
    delete_conversation,
    get_conversation,
    get_conversation_messages,
    get_user_conversations,
    update_conversation,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateConversationRequest(BaseModel):
    title: str = Field(default="New Chat", max_length=200)


class UpdateConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class ConversationResponse(BaseModel):
    conversation: Dict[str, Any]


class ConversationWithMessagesResponse(BaseModel):
    conversation: Dict[str, Any]
    messages: List[Dict[str, Any]]


class ConversationListResponse(BaseModel):
    conversations: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=ConversationListResponse)
async def list_conversations(user: Dict[str, Any] = Depends(get_current_user)):
    """List all conversations for the authenticated user."""
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    conversations = get_user_conversations(db, user["id"])
    return ConversationListResponse(conversations=conversations)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_new_conversation(
    request: CreateConversationRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new conversation."""
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    conversation = create_conversation(
        db,
        user_id=user["id"],
        title=request.title,
    )
    return ConversationResponse(conversation=conversation)


@router.get("/{conversation_id}", response_model=ConversationWithMessagesResponse)
async def get_conversation_detail(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get a conversation with all its messages."""
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    conversation = get_conversation(db, conversation_id, user["id"])
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    messages = get_conversation_messages(db, conversation_id)
    return ConversationWithMessagesResponse(
        conversation=conversation,
        messages=messages,
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def rename_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Rename a conversation."""
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    updated = update_conversation(
        db, conversation_id, user["id"],
        {"title": request.title},
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return ConversationResponse(conversation=updated)


@router.delete("/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    deleted = delete_conversation(db, conversation_id, user["id"])
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return {"message": "Conversation deleted"}
