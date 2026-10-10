"""Admin API routes.

Provides secure admin authentication, stats, knowledge gaps analysis with CSV export,
user feedback tracking, user administration, and system diagnostics.
All endpoints except login require the 'admin' role.
"""
from __future__ import annotations

import csv
import io
import os
import platform
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.auth import create_token, require_admin, verify_password
from app.cache import get_cache
from app.database import get_db
from app.models import (
    _oid,
    find_user_by_email,
    get_conversation_count,
    get_feedback_stats,
    get_user_count,
)
from app.utils import logger

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Rate Limiting: 5 attempts per 15 minutes
# ---------------------------------------------------------------------------
_ADMIN_LOGIN_ATTEMPTS: Dict[str, List[float]] = {}
ADMIN_MAX_ATTEMPTS = 5
ADMIN_WINDOW_SECONDS = 15 * 60  # 15 minutes


class AdminLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def admin_login(req: AdminLoginRequest, request: Request):
    """Admin-only login with brute-force rate limiting and 2-hour JWT."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{req.email.lower()}"
    now = time.time()

    # Clean old attempts
    attempts = _ADMIN_LOGIN_ATTEMPTS.get(rate_key, [])
    attempts = [t for t in attempts if now - t < ADMIN_WINDOW_SECONDS]
    _ADMIN_LOGIN_ATTEMPTS[rate_key] = attempts

    if len(attempts) >= ADMIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait 15 minutes before trying again.",
        )

    db = get_db()
    user = find_user_by_email(db, req.email) if db is not None else None

    # 1. Check against MongoDB user with admin role
    if user and user.get("role") == "admin":
        if verify_password(req.password, user.get("password_hash", "")):
            _ADMIN_LOGIN_ATTEMPTS.pop(rate_key, None)
            token = create_token(user["id"], role="admin", expiration_hours=2)
            return {
                "token": token,
                "user": {
                    "id": user["id"],
                    "name": user.get("name", "Administrator"),
                    "email": user["email"],
                    "role": "admin",
                },
            }

    # 2. Check against environment ADMIN_EMAIL and ADMIN_PASSWORD
    env_admin_email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    env_admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    if env_admin_email and req.email.lower() == env_admin_email and req.password == env_admin_pass:
        _ADMIN_LOGIN_ATTEMPTS.pop(rate_key, None)
        admin_id = user["id"] if user else "admin_system_id"
        token = create_token(admin_id, role="admin", expiration_hours=2)
        return {
            "token": token,
            "user": {
                "id": admin_id,
                "name": "Administrator",
                "email": req.email,
                "role": "admin",
            },
        }

    # Record failed attempt
    _ADMIN_LOGIN_ATTEMPTS[rate_key].append(now)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin credentials",
    )


# ---------------------------------------------------------------------------
# Statistics & Analytics
# ---------------------------------------------------------------------------

@router.get("/stats")
async def admin_stats(user: Dict[str, Any] = Depends(require_admin)):
    """Get system and chat statistics. Admin only."""
    db = get_db()
    stats = {
        "users": 0,
        "conversations": 0,
        "total_queries": 0,
        "knowledge_gaps": 0,
        "feedback": {"thumbs_up": 0, "thumbs_down": 0, "total": 0, "feedback_rate": 0.0},
        "database_connected": db is not None,
    }

    if db is not None:
        try:
            stats["users"] = get_user_count(db)
            stats["conversations"] = get_conversation_count(db)
            stats["total_queries"] = db.chat_events.count_documents({})
            stats["knowledge_gaps"] = db.chat_events.count_documents({"is_gap": True})
            stats["feedback"] = get_feedback_stats(db)
        except Exception as exc:
            logger.warning("Failed to collect DB stats: %s", exc)

    # RAG pipeline status
    api_module = sys.modules.get("api")
    stats["rag_ready"] = getattr(api_module, "_rag_ready", False) if api_module else False

    # Vector store count
    try:
        from app.retriever import get_retriever
        retriever = get_retriever()
        if retriever and retriever.vector_store:
            stats["vector_store_documents"] = retriever.vector_store._collection.count()
    except Exception:
        stats["vector_store_documents"] = None

    # Cache statistics
    try:
        cache = get_cache()
        stats["cache"] = cache.get_stats()
    except Exception:
        stats["cache"] = {"error": "Cache not available"}

    return stats


# ---------------------------------------------------------------------------
# Knowledge Gaps (Unanswered Queries & Missing Information)
# ---------------------------------------------------------------------------

@router.get("/knowledge-gaps")
async def admin_knowledge_gaps(user: Dict[str, Any] = Depends(require_admin)):
    """Get recent unanswered questions and knowledge gaps. Admin only."""
    db = get_db()
    gaps = []
    if db is not None:
        try:
            cursor = db.chat_events.find({"is_gap": True}).sort("timestamp", -1).limit(100)
            for doc in cursor:
                ts = doc.get("timestamp")
                ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                gaps.append({
                    "id": str(doc["_id"]),
                    "question": doc.get("question", ""),
                    "topic": doc.get("topic", "general"),
                    "programmes": doc.get("programmes", []),
                    "status": doc.get("status", ""),
                    "timestamp": ts_str,
                    "latency_s": doc.get("latency_s", 0),
                })
        except Exception as exc:
            logger.error("Failed to query knowledge gaps: %s", exc)

    return {"gaps": gaps, "total": len(gaps)}


@router.get("/knowledge-gaps/csv")
async def export_knowledge_gaps_csv(user: Dict[str, Any] = Depends(require_admin)):
    """Export knowledge gaps as downloadable CSV. Admin only."""
    db = get_db()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Query", "Topic", "Programmes", "Status", "Timestamp UTC", "Latency Seconds"])

    if db is not None:
        try:
            cursor = db.chat_events.find({"is_gap": True}).sort("timestamp", -1).limit(500)
            for doc in cursor:
                ts = doc.get("timestamp")
                ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                progs = ", ".join(doc.get("programmes", []))
                writer.writerow([
                    doc.get("question", ""),
                    doc.get("topic", "general"),
                    progs,
                    doc.get("status", ""),
                    ts_str,
                    doc.get("latency_s", 0),
                ])
        except Exception as exc:
            logger.error("Failed to export knowledge gaps CSV: %s", exc)

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=charusat_knowledge_gaps.csv"},
    )


# ---------------------------------------------------------------------------
# Feedback Tracking
# ---------------------------------------------------------------------------

@router.get("/feedback")
async def admin_feedback(user: Dict[str, Any] = Depends(require_admin)):
    """Get user feedback events and rated messages. Admin only."""
    db = get_db()
    items = []
    stats = {"thumbs_up": 0, "thumbs_down": 0, "total": 0, "feedback_rate": 0.0}

    if db is not None:
        try:
            stats = get_feedback_stats(db)
            cursor = db.messages.find({"feedback": {"$in": ["thumbs_up", "thumbs_down"]}}).sort("created_at", -1).limit(100)
            for m in cursor:
                ts = m.get("created_at")
                ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                content = m.get("content", "")
                items.append({
                    "id": str(m["_id"]),
                    "conversation_id": str(m.get("conversation_id", "")),
                    "feedback": m.get("feedback"),
                    "preview": (content[:160] + "...") if len(content) > 160 else content,
                    "timestamp": ts_str,
                })
        except Exception as exc:
            logger.error("Failed to query feedback: %s", exc)

    return {"feedback_items": items, "stats": stats}


# ---------------------------------------------------------------------------
# User Administration
# ---------------------------------------------------------------------------

@router.get("/users")
async def admin_users(user: Dict[str, Any] = Depends(require_admin)):
    """List registered users. Admin only."""
    db = get_db()
    users_list = []
    if db is not None:
        try:
            cursor = db.users.find({}, {"password_hash": 0}).sort("created_at", -1).limit(100)
            for u in cursor:
                u_id = str(u["_id"])
                conv_count = db.conversations.count_documents({"user_id": _oid(u_id)})
                ts = u.get("created_at")
                ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                users_list.append({
                    "id": u_id,
                    "name": u.get("name", "User"),
                    "email": u.get("email", ""),
                    "role": u.get("role", "user"),
                    "auth_provider": u.get("auth_provider", "local"),
                    "created_at": ts_str,
                    "conversations_count": conv_count,
                })
        except Exception as exc:
            logger.error("Failed to list users: %s", exc)

    return {"users": users_list, "total": len(users_list)}


# ---------------------------------------------------------------------------
# System Diagnostics & Cache
# ---------------------------------------------------------------------------

@router.get("/system")
async def admin_system(user: Dict[str, Any] = Depends(require_admin)):
    """Get system diagnostics, vector store health, and environment config. Admin only."""
    db = get_db()
    from app import config

    vector_count = None
    try:
        from app.retriever import get_retriever
        retriever = get_retriever()
        if retriever and retriever.vector_store:
            vector_count = retriever.vector_store._collection.count()
    except Exception:
        pass

    api_module = sys.modules.get("api")
    rag_ready = getattr(api_module, "_rag_ready", False) if api_module else False

    return {
        "python_version": sys.version.split()[0],
        "os_platform": platform.platform(),
        "database_connected": db is not None,
        "database_name": db.name if db is not None else None,
        "collections": db.list_collection_names() if db is not None else [],
        "rag_ready": rag_ready,
        "vector_store_documents": vector_count,
        "llm_preferred_models": list(config.PREFERRED_MODELS),
        "llm_temperature": config.LLM_TEMPERATURE,
        "groq_failover_model": getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile"),
        "min_relevance_score": config.MIN_RELEVANCE_SCORE,
    }


@router.get("/cache")
async def cache_stats(user: Dict[str, Any] = Depends(require_admin)):
    """Get cache statistics. Admin only."""
    try:
        cache = get_cache()
        return cache.get_stats()
    except Exception as exc:
        return {"error": str(exc)}


@router.delete("/cache")
async def clear_cache(user: Dict[str, Any] = Depends(require_admin)):
    """Clear the question cache. Admin only."""
    try:
        cache = get_cache()
        cache.clear()
        return {"message": "Cache cleared successfully"}
    except Exception as exc:
        return {"error": str(exc)}
