"""Routes for as-you-type question suggestions."""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import get_optional_user
from app.database import get_db
from app.suggest_service import generate_suggestions

router = APIRouter(tags=["suggest"])


class SuggestItem(BaseModel):
    text: str
    topic: str


class SuggestRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100)
    conversation_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    programme: Optional[str] = None


class SuggestResponse(BaseModel):
    suggestions: List[SuggestItem] = []


def _get_retriever_from_api():
    """Retrieve active retriever instance from the running api module."""
    api_mod = sys.modules.get("api")
    if api_mod is not None:
        retriever = getattr(api_mod, "retriever", None)
        if retriever is not None:
            return retriever
        rag_chain = getattr(api_mod, "rag_chain", None)
        if rag_chain is not None and hasattr(rag_chain, "retriever"):
            return rag_chain.retriever
    return None


@router.post("/api/suggest", response_model=SuggestResponse)
async def suggest_questions(
    req: SuggestRequest,
    request: Request,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    db: Any = Depends(get_db),
):
    """Return up to 5 as-you-type question suggestions."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    retriever = _get_retriever_from_api()

    suggestions = await generate_suggestions(
        text=req.text,
        conversation_id=req.conversation_id,
        history=req.history,
        programme=req.programme,
        user=user,
        client_ip=client_ip,
        retriever=retriever,
        db=db,
    )

    return SuggestResponse(
        suggestions=[SuggestItem(text=s["text"], topic=s["topic"]) for s in suggestions]
    )
