"""Admin API routes.

Provides secure admin authentication, stats and overview aggregates,
knowledge gaps analysis with formula-safe UTF-8 BOM CSV export,
conversations inspection with masked user emails and audit-logged reveals,
feedback review queue, user management with disable/delete,
read-only knowledge base inventory, system diagnostics, and audit logging.

All endpoints except login require the 'admin' role.
"""
from __future__ import annotations

import csv
import io
import math
import os
import platform
import re
import string
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app.auth import create_token, get_current_user, require_admin, verify_password
from app.cache import get_cache
from app.database import get_db
from app.models import (
    _oid,
    find_user_by_email,
    find_user_by_id,
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


# ---------------------------------------------------------------------------
# Helpers: Audit Logging, Masking & CSV Sanitization
# ---------------------------------------------------------------------------

def log_audit_event(
    db: Any,
    admin_user: Dict[str, Any],
    action: str,
    target_type: str,
    target_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    """Write an append-only audit record for all admin write actions and reveals."""
    if db is None:
        return
    try:
        record = {
            "admin_id": str(admin_user.get("id", "")),
            "admin_email": admin_user.get("email", "unknown"),
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id) if target_id else None,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        db.audit_log.insert_one(record)
    except Exception as exc:
        logger.warning("Failed to record audit event: %s", exc)


def mask_email(email: Optional[str]) -> str:
    """Mask user email for privacy (e.g. s***@charusat.edu.in)."""
    if not email or "@" not in email:
        return "anonymous"
    user_part, domain = email.split("@", 1)
    if len(user_part) <= 1:
        masked = user_part + "***"
    elif len(user_part) == 2:
        masked = user_part[0] + "***"
    else:
        masked = user_part[0] + "***" + user_part[-1]
    return f"{masked}@{domain}"


def sanitize_csv_cell(val: Any) -> str:
    """Neutralize formula injection by prefixing dangerous characters with an apostrophe."""
    s = str(val) if val is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def normalize_question(q: str) -> str:
    """Normalize question by lowercasing and stripping punctuation for grouping."""
    if not q:
        return ""
    q = q.lower().strip()
    return re.sub(r"[^\w\s]", "", q).strip()


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class AdminLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class UpdateGapRequest(BaseModel):
    review_status: str = Field(..., description="open, in_progress, resolved, or ignored")
    note: Optional[str] = Field(None, max_length=1000)


class UpdateFeedbackRequest(BaseModel):
    review_status: str = Field(..., description="open, reviewed, or resolved")
    note: Optional[str] = Field(None, max_length=1000)


class UpdateUserRequest(BaseModel):
    role: Optional[str] = Field(None, description="user or admin")
    is_disabled: Optional[bool] = None


# ---------------------------------------------------------------------------
# 1. Admin Authentication
# ---------------------------------------------------------------------------

@router.post("/login")
async def admin_login(req: AdminLoginRequest, request: Request):
    """Admin-only sign-in with brute-force protection and database role verification."""
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
            detail="Too many failed login attempts. Please try again in 15 minutes.",
        )

    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    user = find_user_by_email(db, req.email)
    if user and user.get("role") == "admin":
        if verify_password(req.password, user.get("password_hash", "")):
            _ADMIN_LOGIN_ATTEMPTS.pop(rate_key, None)
            token = create_token(user["id"], role="admin", expiration_hours=2)
            log_audit_event(db, user, "admin_login", "auth", user["id"], {"ip": client_ip})
            return {
                "token": token,
                "user": {
                    "id": user["id"],
                    "name": user.get("name", "Administrator"),
                    "email": user["email"],
                    "role": "admin",
                },
            }

    _ADMIN_LOGIN_ATTEMPTS[rate_key].append(now)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin credentials",
    )


# ---------------------------------------------------------------------------
# 2. Overview & Analytics
# ---------------------------------------------------------------------------

@router.get("/overview")
async def admin_overview(
    days: int = Query(7, ge=1, le=90),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Get aggregated analytics over the selected date range (7, 30, 90 days)."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    # 1. Queries and Gaps aggregation per day
    events_cursor = db.chat_events.find({"timestamp": {"$gte": cutoff}})
    daily_stats: Dict[str, Dict[str, int]] = {}
    latencies: List[float] = []
    total_queries = 0
    total_gaps = 0

    # Pre-populate all days in range
    for i in range(days):
        day_str = (cutoff + timedelta(days=i)).strftime("%Y-%m-%d")
        daily_stats[day_str] = {"total": 0, "answered": 0, "gaps": 0}

    for doc in events_cursor:
        total_queries += 1
        is_gap = bool(doc.get("is_gap"))
        if is_gap:
            total_gaps += 1

        ts = doc.get("timestamp")
        if isinstance(ts, datetime):
            day_str = ts.strftime("%Y-%m-%d")
        else:
            try:
                day_str = str(ts)[:10]
            except Exception:
                day_str = now.strftime("%Y-%m-%d")

        if day_str not in daily_stats:
            daily_stats[day_str] = {"total": 0, "answered": 0, "gaps": 0}

        daily_stats[day_str]["total"] += 1
        if is_gap:
            daily_stats[day_str]["gaps"] += 1
        else:
            daily_stats[day_str]["answered"] += 1

        lat = doc.get("latency_s")
        if lat and isinstance(lat, (int, float)) and lat > 0:
            latencies.append(float(lat))

    queries_per_day = [
        {"date": d, "total": s["total"], "answered": s["answered"], "gaps": s["gaps"]}
        for d, s in sorted(daily_stats.items())
    ]

    # Latency percentiles
    latencies.sort()
    median_latency = 0.0
    p95_latency = 0.0
    if latencies:
        median_latency = round(latencies[len(latencies) // 2], 3)
        p95_idx = int(len(latencies) * 0.95)
        p95_latency = round(latencies[min(p95_idx, len(latencies) - 1)], 3)

    # Cache stats
    cache_hit_rate = 0.0
    try:
        cache = get_cache()
        c_stats = cache.get_stats()
        hits = c_stats.get("hits", 0)
        misses = c_stats.get("misses", 0)
        total_c = hits + misses
        if total_c > 0:
            cache_hit_rate = round(hits / total_c, 3)
    except Exception:
        pass

    # Users in range
    new_users = db.users.count_documents({"created_at": {"$gte": cutoff}})
    total_users = db.users.count_documents({})

    # Feedback in range
    fb_stats = get_feedback_stats(db)
    up = fb_stats.get("thumbs_up", 0)
    down = fb_stats.get("thumbs_down", 0)
    total_ratings = up + down
    feedback_rate = round(total_ratings / total_queries, 4) if total_queries > 0 else 0.0
    positive_share = round(up / total_ratings, 3) if total_ratings >= 20 else None

    return {
        "range_days": days,
        "total_queries": total_queries,
        "answered_queries": total_queries - total_gaps,
        "gap_queries": total_gaps,
        "gap_rate": round(total_gaps / total_queries, 3) if total_queries > 0 else 0.0,
        "queries_per_day": queries_per_day,
        "median_latency_s": median_latency,
        "p95_latency_s": p95_latency,
        "cache_hit_rate": cache_hit_rate,
        "new_users": new_users,
        "total_users": total_users,
        "feedback": {
            "thumbs_up": up,
            "thumbs_down": down,
            "total_ratings": total_ratings,
            "feedback_rate": feedback_rate,
            "positive_share": positive_share,
            "enough_ratings": total_ratings >= 20,
        },
    }


# Backwards compatible alias for old stats endpoint
@router.get("/stats")
async def admin_stats(user: Dict[str, Any] = Depends(require_admin)):
    """Legacy stats endpoint mapped to current database state."""
    db = get_db()
    stats = {
        "users": get_user_count(db) if db is not None else 0,
        "conversations": get_conversation_count(db) if db is not None else 0,
        "total_queries": db.chat_events.count_documents({}) if db is not None else 0,
        "knowledge_gaps": db.chat_events.count_documents({"is_gap": True}) if db is not None else 0,
        "feedback": get_feedback_stats(db) if db is not None else {"thumbs_up": 0, "thumbs_down": 0, "total": 0, "feedback_rate": 0.0},
        "database_connected": db is not None,
    }
    return stats


# ---------------------------------------------------------------------------
# 3. Knowledge Gaps (Grouped, Searchable, Workflow Actions)
# ---------------------------------------------------------------------------

@router.get("/knowledge-gaps")
async def admin_knowledge_gaps(
    topic: Optional[str] = None,
    programme: Optional[str] = None,
    review_status: Optional[str] = None,
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Get knowledge gaps grouped by normalized question, frequency, and status."""
    db = get_db()
    if db is None:
        return {"gaps": [], "total": 0, "page": page, "pages": 1}

    query_filter: Dict[str, Any] = {"is_gap": True}
    if topic:
        query_filter["topic"] = topic
    if programme:
        query_filter["programmes"] = programme
    if review_status:
        query_filter["review_status"] = review_status
    if q:
        query_filter["question"] = {"$regex": re.escape(q), "$options": "i"}

    # Fetch gaps up to 1000 for client grouping
    cursor = db.chat_events.find(query_filter).sort("timestamp", -1).limit(1000)

    grouped: Dict[str, Dict[str, Any]] = {}
    for doc in cursor:
        raw_q = doc.get("question", "")
        norm = normalize_question(raw_q) or raw_q
        ts = doc.get("timestamp")
        ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)

        if norm not in grouped:
            grouped[norm] = {
                "id": str(doc["_id"]),
                "normalized_question": norm,
                "question": raw_q,
                "count": 0,
                "topic": doc.get("topic", "general"),
                "programmes": doc.get("programmes", []),
                "status": doc.get("status", ""),
                "review_status": doc.get("review_status", "open") or "open",
                "note": doc.get("note", ""),
                "last_seen": ts_str,
                "resolved_at": doc.get("resolved_at"),
                "resolved_by": doc.get("resolved_by"),
            }
        grouped[norm]["count"] += 1

    # Sort grouped by count descending
    sorted_groups = sorted(grouped.values(), key=lambda x: x["count"], reverse=True)
    total_items = len(sorted_groups)
    start_idx = (page - 1) * limit
    paged = sorted_groups[start_idx : start_idx + limit]

    return {
        "gaps": paged,
        "total": total_items,
        "page": page,
        "limit": limit,
        "pages": max(1, math.ceil(total_items / limit)),
    }


@router.patch("/knowledge-gaps/{gap_id}")
async def update_knowledge_gap(
    gap_id: str,
    req: UpdateGapRequest,
    user: Dict[str, Any] = Depends(require_admin),
):
    """Update workflow review_status and note on a knowledge gap. Audited."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        oid = _oid(gap_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid gap ID")

    gap = db.chat_events.find_one({"_id": oid})
    if not gap:
        raise HTTPException(status_code=404, detail="Knowledge gap not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    updates = {
        "review_status": req.review_status,
        "note": req.note,
    }
    if req.review_status in ("resolved", "ignored"):
        updates["resolved_at"] = now_iso
        updates["resolved_by"] = user.get("email")

    db.chat_events.update_one({"_id": oid}, {"$set": updates})

    log_audit_event(
        db,
        user,
        "update_knowledge_gap",
        "knowledge_gap",
        gap_id,
        {"review_status": req.review_status, "question": gap.get("question")},
    )

    return {"status": "success", "message": "Knowledge gap updated successfully"}


@router.get("/knowledge-gaps/csv")
async def export_knowledge_gaps_csv(
    topic: Optional[str] = None,
    programme: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_admin),
):
    """Export knowledge gaps as downloadable CSV with UTF-8 BOM and formula neutralization."""
    db = get_db()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Query",
        "Frequency Count",
        "Topic",
        "Programmes",
        "Review Status",
        "Note",
        "Last Seen UTC",
    ])

    if db is not None:
        query_filter: Dict[str, Any] = {"is_gap": True}
        if topic:
            query_filter["topic"] = topic
        if programme:
            query_filter["programmes"] = programme

        cursor = db.chat_events.find(query_filter).sort("timestamp", -1).limit(1000)
        grouped: Dict[str, Dict[str, Any]] = {}
        for doc in cursor:
            raw_q = doc.get("question", "")
            norm = normalize_question(raw_q) or raw_q
            ts = doc.get("timestamp")
            ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)

            if norm not in grouped:
                grouped[norm] = {
                    "question": raw_q,
                    "count": 0,
                    "topic": doc.get("topic", "general"),
                    "programmes": ", ".join(doc.get("programmes", [])),
                    "review_status": doc.get("review_status", "open") or "open",
                    "note": doc.get("note", ""),
                    "last_seen": ts_str,
                }
            grouped[norm]["count"] += 1

        for item in sorted(grouped.values(), key=lambda x: x["count"], reverse=True):
            writer.writerow([
                sanitize_csv_cell(item["question"]),
                item["count"],
                sanitize_csv_cell(item["topic"]),
                sanitize_csv_cell(item["programmes"]),
                sanitize_csv_cell(item["review_status"]),
                sanitize_csv_cell(item["note"]),
                sanitize_csv_cell(item["last_seen"]),
            ])

    # Prepend UTF-8 BOM so Excel opens Hindi/Gujarati scripts correctly
    csv_bytes = b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=charusat_knowledge_gaps.csv"},
    )


# ---------------------------------------------------------------------------
# 4. Conversations Inspection (Read-Only Transcripts & Audited Reveal)
# ---------------------------------------------------------------------------

@router.get("/conversations")
async def list_admin_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_admin),
):
    """List conversations across all users with masked user emails for quality review."""
    db = get_db()
    if db is None:
        return {"conversations": [], "total": 0}

    query_filter: Dict[str, Any] = {}
    if q:
        query_filter["title"] = {"$regex": re.escape(q), "$options": "i"}

    total = db.conversations.count_documents(query_filter)
    cursor = (
        db.conversations.find(query_filter)
        .sort("updated_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    items = []
    for conv in cursor:
        conv_id = str(conv["_id"])
        user_oid = conv.get("user_id")
        user_email = None
        if user_oid:
            u = db.users.find_one({"_id": user_oid})
            if u:
                user_email = u.get("email")

        msg_count = db.messages.count_documents({"conversation_id": _oid(conv_id)})
        ts = conv.get("updated_at") or conv.get("created_at")
        ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)

        items.append({
            "id": conv_id,
            "title": conv.get("title", "Untitled"),
            "user_email_masked": mask_email(user_email),
            "has_user": bool(user_email),
            "message_count": msg_count,
            "updated_at": ts_str,
        })

    return {
        "conversations": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, math.ceil(total / limit)),
    }


@router.get("/conversations/{conversation_id}")
async def get_admin_conversation_transcript(
    conversation_id: str,
    user: Dict[str, Any] = Depends(require_admin),
):
    """View read-only conversation transcript for quality review."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        oid = _oid(conversation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    conv = db.conversations.find_one({"_id": oid})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_email = None
    if conv.get("user_id"):
        u = db.users.find_one({"_id": conv["user_id"]})
        if u:
            user_email = u.get("email")

    messages_cursor = db.messages.find({"conversation_id": oid}).sort("created_at", 1)
    messages = []
    for m in messages_cursor:
        ts = m.get("created_at")
        ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        messages.append({
            "id": str(m["_id"]),
            "role": m.get("role"),
            "content": m.get("content"),
            "sources": m.get("sources", []),
            "feedback": m.get("feedback"),
            "feedback_reason": m.get("feedback_reason"),
            "timestamp": ts_str,
        })

    return {
        "conversation": {
            "id": conversation_id,
            "title": conv.get("title", "Untitled"),
            "user_email_masked": mask_email(user_email),
            "created_at": conv.get("created_at"),
            "messages": messages,
        }
    }


@router.post("/conversations/{conversation_id}/reveal")
async def reveal_conversation_user_email(
    conversation_id: str,
    user: Dict[str, Any] = Depends(require_admin),
):
    """Explicitly reveal user email for a conversation. Audited."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        oid = _oid(conversation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    conv = db.conversations.find_one({"_id": oid})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_email = "Guest / anonymous"
    if conv.get("user_id"):
        u = db.users.find_one({"_id": conv["user_id"]})
        if u:
            user_email = u.get("email", "unknown")

    log_audit_event(
        db,
        user,
        "email_reveal",
        "conversation",
        conversation_id,
        {"revealed_email": user_email},
    )

    return {"user_email": user_email}


# ---------------------------------------------------------------------------
# 5. Feedback Review Queue
# ---------------------------------------------------------------------------

@router.get("/feedback")
async def admin_feedback(
    feedback_type: Optional[str] = Query(None, description="thumbs_up or thumbs_down"),
    review_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Get feedback review queue showing question, answer, sources, and reason."""
    db = get_db()
    if db is None:
        return {"feedback_items": [], "total": 0, "stats": {}}

    query_filter: Dict[str, Any] = {}
    if feedback_type:
        query_filter["feedback"] = feedback_type
    else:
        query_filter["feedback"] = {"$in": ["thumbs_up", "thumbs_down"]}

    if review_status:
        query_filter["review_status"] = review_status

    total = db.messages.count_documents(query_filter)
    cursor = (
        db.messages.find(query_filter)
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    items = []
    for m in cursor:
        m_id = str(m["_id"])
        c_id = str(m.get("conversation_id", ""))

        # Find matching user question if possible
        question_text = ""
        prev_user_msg = db.messages.find_one(
            {"conversation_id": m.get("conversation_id"), "role": "user", "_id": {"$lt": m["_id"]}},
            sort=[("_id", -1)],
        )
        if prev_user_msg:
            question_text = prev_user_msg.get("content", "")

        ts = m.get("created_at")
        ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        items.append({
            "id": m_id,
            "conversation_id": c_id,
            "feedback": m.get("feedback"),
            "reason": m.get("feedback_reason"),
            "question": question_text,
            "answer": m.get("content", ""),
            "sources": m.get("sources", []),
            "review_status": m.get("review_status", "open") or "open",
            "review_note": m.get("review_note", ""),
            "timestamp": ts_str,
        })

    stats = get_feedback_stats(db)
    return {
        "feedback_items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "stats": stats,
    }


@router.patch("/feedback/{message_id}")
async def update_feedback_review(
    message_id: str,
    req: UpdateFeedbackRequest,
    user: Dict[str, Any] = Depends(require_admin),
):
    """Mark feedback as reviewed or resolved. Audited."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        oid = _oid(message_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid message ID")

    now_iso = datetime.now(timezone.utc).isoformat()
    db.messages.update_one(
        {"_id": oid},
        {
            "$set": {
                "review_status": req.review_status,
                "review_note": req.note,
                "reviewed_at": now_iso,
                "reviewed_by": user.get("email"),
            }
        },
    )

    log_audit_event(
        db,
        user,
        "update_feedback",
        "feedback",
        message_id,
        {"review_status": req.review_status},
    )

    return {"status": "success", "message": "Feedback review updated successfully"}


# ---------------------------------------------------------------------------
# 6. User Administration
# ---------------------------------------------------------------------------

@router.get("/users")
async def admin_users(
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user: Dict[str, Any] = Depends(require_admin),
):
    """List registered users with pagination and search."""
    db = get_db()
    if db is None:
        return {"users": [], "total": 0}

    query_filter: Dict[str, Any] = {}
    if q:
        query_filter["$or"] = [
            {"email": {"$regex": re.escape(q), "$options": "i"}},
            {"name": {"$regex": re.escape(q), "$options": "i"}},
        ]

    total = db.users.count_documents(query_filter)
    cursor = (
        db.users.find(query_filter, {"password_hash": 0})
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    users_list = []
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
            "is_disabled": bool(u.get("is_disabled") or u.get("disabled")),
            "auth_provider": u.get("auth_provider", "local"),
            "created_at": ts_str,
            "conversations_count": conv_count,
        })

    return {
        "users": users_list,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, math.ceil(total / limit)),
    }


@router.patch("/users/{user_id}")
async def update_user_status(
    user_id: str,
    req: UpdateUserRequest,
    user: Dict[str, Any] = Depends(require_admin),
):
    """Change user role or disable/enable account. Cannot demote self. Audited."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        oid = _oid(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    target = db.users.find_one({"_id": oid})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Protection: Admin cannot demote or disable themselves
    if str(user.get("id")) == user_id:
        if req.role and req.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove admin privileges from your own account",
            )
        if req.is_disabled is True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot disable your own account",
            )

    updates: Dict[str, Any] = {}
    if req.role is not None:
        if req.role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'user'")
        updates["role"] = req.role

    if req.is_disabled is not None:
        updates["is_disabled"] = req.is_disabled

    if updates:
        db.users.update_one({"_id": oid}, {"$set": updates})
        log_audit_event(
            db,
            user,
            "update_user",
            "user",
            user_id,
            {"target_email": target.get("email"), "updates": updates},
        )

    return {"status": "success", "message": "User updated successfully"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: Dict[str, Any] = Depends(require_admin),
):
    """Delete a user and all their conversation data. Cannot delete self. Audited."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    if str(user.get("id")) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own admin account",
        )

    try:
        oid = _oid(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    target = db.users.find_one({"_id": oid})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete all conversations and messages
    conv_ids = [c["_id"] for c in db.conversations.find({"user_id": oid}, {"_id": 1})]
    if conv_ids:
        db.messages.delete_many({"conversation_id": {"$in": conv_ids}})
        db.conversations.delete_many({"user_id": oid})

    db.users.delete_one({"_id": oid})

    log_audit_event(
        db,
        user,
        "delete_user",
        "user",
        user_id,
        {"deleted_email": target.get("email")},
    )

    return {"status": "success", "message": f"User {target.get('email')} and all associated data deleted"}


# ---------------------------------------------------------------------------
# 7. Knowledge Base Inventory (Read-Only)
# ---------------------------------------------------------------------------

@router.get("/knowledge-base")
async def admin_knowledge_base(user: Dict[str, Any] = Depends(require_admin)):
    """Read-only view of documents and chunks in the vector database."""
    docs_by_prog: Dict[str, int] = {"bba": 0, "bca": 0, "mba": 0, "mca": 0, "general": 0}
    doc_sources: Dict[str, Dict[str, Any]] = {}
    total_chunks = 0
    last_modified = None

    try:
        from app.embeddings import EmbeddingStore
        embedding_store = EmbeddingStore()
        vector_store = embedding_store.load_vector_store()
        if vector_store:
            collection = vector_store._collection
            total_chunks = collection.count()

            # Read sample or all metadata
            all_meta = collection.get(include=["metadatas"])
            for m in (all_meta.get("metadatas") or []):
                if not m:
                    continue
                prog = str(m.get("program_name") or "general").lower()
                if "bba" in prog:
                    docs_by_prog["bba"] += 1
                elif "bca" in prog:
                    docs_by_prog["bca"] += 1
                elif "mba" in prog:
                    docs_by_prog["mba"] += 1
                elif "mca" in prog:
                    docs_by_prog["mca"] += 1
                else:
                    docs_by_prog["general"] += 1

                source = str(m.get("source") or "unknown")
                if source not in doc_sources:
                    doc_sources[source] = {
                        "name": os.path.basename(source),
                        "source": source,
                        "program": prog,
                        "chunk_count": 0,
                    }
                doc_sources[source]["chunk_count"] += 1
    except Exception as exc:
        logger.warning("Could not read full vector store breakdown: %s", exc)

    # Check last ingestion timestamp from manifest or folder stat
    manifest_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base")
    try:
        if os.path.exists(manifest_path):
            stat = os.stat(manifest_path)
            last_modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
    except Exception:
        pass

    return {
        "total_chunks": total_chunks,
        "total_documents": len(doc_sources),
        "documents": list(doc_sources.values()),
        "chunks_per_programme": docs_by_prog,
        "last_ingested_at": last_modified,
        "rebuild_note": "Rebuilding the vector store index is a server-side CLI task (python ingest_pdfs.py).",
    }


# ---------------------------------------------------------------------------
# 8. Audit Log
# ---------------------------------------------------------------------------

@router.get("/audit-log")
async def get_audit_log(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Get paginated append-only audit log."""
    db = get_db()
    if db is None:
        return {"logs": [], "total": 0}

    total = db.audit_log.count_documents({})
    cursor = (
        db.audit_log.find({})
        .sort("timestamp", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    logs = []
    for l in cursor:
        logs.append({
            "id": str(l["_id"]),
            "admin_email": l.get("admin_email", "unknown"),
            "action": l.get("action", ""),
            "target_type": l.get("target_type", ""),
            "target_id": l.get("target_id"),
            "details": l.get("details", {}),
            "timestamp": l.get("timestamp"),
        })

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, math.ceil(total / limit)),
    }


# ---------------------------------------------------------------------------
# 9. System Diagnostics & Cache
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
    """Clear the question cache with audit log. Admin only."""
    try:
        cache = get_cache()
        cache.clear()
        db = get_db()
        log_audit_event(db, user, "clear_cache", "cache", None, {})
        return {"status": "success", "message": "Cache cleared successfully"}
    except Exception as exc:
        return {"error": str(exc)}
