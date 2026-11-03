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
from pathlib import Path
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
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File, status
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
    """Get aggregated analytics over the selected date range (7, 30, 90 days).
    Derived from ONE aggregation over chat_events in the selected window.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    cutoff_iso = cutoff.isoformat()

    daily_stats: Dict[str, Dict[str, int]] = {}
    for i in range(days):
        day_str = (cutoff + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        daily_stats[day_str] = {"total": 0, "answered": 0, "gaps": 0}

    query = {"$or": [{"timestamp": {"$gte": cutoff}}, {"timestamp": {"$gte": cutoff_iso}}]}
    cursor = db.chat_events.find(query)

    total_queries = 0
    total_gaps = 0
    latencies: List[float] = []
    distinct_users: set = set()
    thumbs_up = 0
    thumbs_down = 0

    for doc in cursor:
        total_queries += 1
        is_gap = bool(doc.get("is_gap"))
        if is_gap:
            total_gaps += 1

        uid = doc.get("user_id")
        if uid:
            distinct_users.add(str(uid))

        fb = doc.get("feedback")
        if fb == "thumbs_up":
            thumbs_up += 1
        elif fb == "thumbs_down":
            thumbs_down += 1

        lat = doc.get("latency_s")
        if lat and isinstance(lat, (int, float)) and lat > 0:
            latencies.append(float(lat))

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

    if thumbs_up == 0 and thumbs_down == 0:
        fb_stats = get_feedback_stats(db)
        thumbs_up = fb_stats.get("thumbs_up", 0)
        thumbs_down = fb_stats.get("thumbs_down", 0)

    total_ratings = thumbs_up + thumbs_down
    gap_rate = round(total_gaps / total_queries, 4) if total_queries > 0 else 0.0
    feedback_rate = round(total_ratings / total_queries, 4) if total_queries > 0 else 0.0
    positive_share = round(thumbs_up / total_ratings, 3) if total_ratings >= 20 else None

    latencies.sort()
    median_latency = round(latencies[len(latencies) // 2], 3) if latencies else 0.0

    queries_per_day = [
        {"date": d, "total": s["total"], "answered": s["answered"], "gaps": s["gaps"]}
        for d, s in sorted(daily_stats.items())
    ]

    return {
        "range_days": days,
        "total_queries": total_queries,
        "answered_queries": total_queries - total_gaps,
        "gap_queries": total_gaps,
        "gap_rate": gap_rate,
        "queries_per_day": queries_per_day,
        "median_latency_s": median_latency,
        "active_users": len(distinct_users),
        "total_users": db.users.count_documents({}),
        "feedback": {
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
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
        "feedback": items,
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

    # Check last ingestion timestamp from last_sync.json, index dir, or knowledge_base dir
    kb_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base")
    last_sync_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend", "last_sync.json")
    try:
        if os.path.exists(last_sync_file):
            import json
            with open(last_sync_file, "r", encoding="utf-8") as f:
                sync_info = json.load(f)
                last_modified = sync_info.get("last_sync") or sync_info.get("timestamp")
        if not last_modified and os.path.exists(kb_dir):
            stat = os.stat(kb_dir)
            last_modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
    except Exception:
        pass

    return {
        "total_chunks": total_chunks,
        "total_documents": len(doc_sources),
        "documents": list(doc_sources.values()),
        "chunks_per_programme": docs_by_prog,
        "last_ingested_at": last_modified,
        "last_modified": last_modified,
        "rebuild_note": "Rebuilding the vector store index is a server-side CLI task (python rebuild_vectordb.py).",
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
    """Get real system diagnostics, vector store health, and environment config. Admin only."""
    db = get_db()
    from app import config

    # Real MongoDB Ping
    mongo_ok = False
    if db is not None:
        try:
            db.command("ping")
            mongo_ok = True
        except Exception as exc:
            logger.warning("MongoDB ping failed: %s", exc)

    # Real Vector Store chunk count from the canonical EmbeddingStore loader
    chunk_count = 0
    try:
        from app.embeddings import EmbeddingStore
        store = EmbeddingStore().load_vector_store()
        if store:
            chunk_count = store._collection.count()
    except Exception as exc:
        logger.warning("Vector store chunk count check failed: %s", exc)

    # Recent admin activity list (last 50 audit entries)
    recent_logs = []
    if db is not None:
        try:
            cursor = db.audit_log.find({}).sort("timestamp", -1).limit(50)
            for entry in cursor:
                ts = entry.get("timestamp")
                ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                recent_logs.append({
                    "id": str(entry["_id"]),
                    "timestamp": ts_str,
                    "admin_email": entry.get("admin_email", "system"),
                    "action": entry.get("action", "unknown"),
                    "target_type": entry.get("target_type"),
                    "target_id": entry.get("target_id"),
                    "details": entry.get("details", {}),
                    "ip_address": entry.get("ip_address"),
                })
        except Exception as exc:
            logger.warning("Failed to load audit logs for system tab: %s", exc)

    # Cache stats
    cache_stats_dict = {}
    try:
        cache = get_cache()
        cache_stats_dict = cache.get_stats()
    except Exception:
        pass

    return {
        "python_version": sys.version.split()[0],
        "os_platform": platform.platform(),
        "build_version": "2026.11.01-v2",
        "database": {
            "connected": mongo_ok,
            "name": db.name if db is not None else None,
        },
        "database_connected": mongo_ok,
        "database_name": db.name if db is not None else None,
        "collections": db.list_collection_names() if (db is not None and mongo_ok) else [],
        "vector_store": {
            "ready": chunk_count > 0,
            "chunks": chunk_count,
            "chunk_count": chunk_count,
        },
        "vector_store_documents": chunk_count,
        "rag_ready": chunk_count > 0,
        "models": {
            "primary": getattr(config, "GEMINI_MODEL", "Gemini 2.5 Flash"),
            "primary_status": "configured",
            "failover": getattr(config, "GROQ_MODEL", "Groq (openai/gpt-oss-120b)"),
            "failover_status": "configured",
        },
        "cache": cache_stats_dict,
        "recent_logs": recent_logs,
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


# ---------------------------------------------------------------------------
# Part 3 & 4: Knowledge Base Manager Endpoints
# ---------------------------------------------------------------------------

class UpdateDraftRequest(BaseModel):
    title: Optional[str] = None
    markdown: Optional[str] = None
    programme: Optional[str] = None
    source_note: Optional[str] = None
    replaces_file: Optional[str] = None


class PublishDraftRequest(BaseModel):
    title: Optional[str] = None
    programme: Optional[str] = None
    source_note: Optional[str] = None


class TestQuestionRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)


class FaqAnswerRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    answer: str = Field(..., min_length=20, max_length=5000)
    source: str = Field(..., min_length=3, max_length=500)
    programme: str = Field(default="GENERAL")
    gap_id: Optional[str] = None


_KB_TEST_RATE_LIMITS: Dict[str, List[float]] = {}


def _check_kb_test_rate_limit(key: str) -> None:
    now = time.time()
    times = _KB_TEST_RATE_LIMITS.get(key, [])
    times = [t for t in times if now - t < 60]
    if len(times) >= 10:
        raise HTTPException(status_code=429, detail="Rate limit exceeded: 10 test questions per minute")
    times.append(now)
    _KB_TEST_RATE_LIMITS[key] = times


@router.post("/kb/convert")
async def kb_convert_file(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Convert uploaded document (PDF, DOCX, MD, TXT) to clean Markdown draft."""
    file_bytes = await file.read()
    filename = file.filename or "uploaded_document.txt"

    from app.kb_manager import convert_file_to_markdown, create_draft
    markdown, warnings, page_count, can_publish = await convert_file_to_markdown(filename, file_bytes)

    draft = create_draft(
        title=Path(filename).stem,
        filename=filename,
        markdown=markdown,
        warnings=warnings,
        page_count=page_count,
        can_publish=can_publish,
        file_bytes=file_bytes,
    )

    db = get_db()
    log_audit_event(
        db,
        user,
        "kb_upload",
        "kb_draft",
        draft["draft_id"],
        {"filename": filename, "page_count": page_count},
    )

    return {
        "draft_id": draft["draft_id"],
        "title": draft["title"],
        "filename": draft["filename"],
        "markdown": draft["markdown"],
        "warnings": draft["warnings"],
        "page_count": draft["page_count"],
        "chunk_estimate": draft["chunk_estimate"],
        "can_publish": draft["can_publish"],
        "programme": draft["programme"],
    }


@router.put("/kb/drafts/{draft_id}")
async def kb_update_draft(
    draft_id: str,
    body: UpdateDraftRequest,
    user: Dict[str, Any] = Depends(require_admin),
):
    """Update draft title, markdown, programme or source notes."""
    from app.kb_manager import update_draft
    updated = update_draft(draft_id, body.dict(exclude_unset=True))
    return updated


@router.post("/kb/drafts/{draft_id}/publish")
async def kb_publish_draft(
    draft_id: str,
    body: Optional[PublishDraftRequest] = None,
    user: Dict[str, Any] = Depends(require_admin),
):
    """Publish draft markdown document to knowledge base and GitHub repository."""
    from app.kb_manager import (
        get_draft,
        validate_safe_slug,
        generate_safe_slug,
        GitHubClient,
        UPLOADS_DIR,
        UPLOADS_ORIGINALS_DIR,
        ensure_upload_dirs,
    )

    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found or expired")
    if not draft.get("can_publish", True):
        raise HTTPException(status_code=400, detail="Document cannot be published (check warnings)")

    ensure_upload_dirs()
    title = (body.title if body and body.title else draft["title"]).strip()
    programme = (body.programme if body and body.programme else draft["programme"]).strip().upper()
    source_note = (body.source_note if body and body.source_note else draft["source_note"]).strip()

    slug = generate_safe_slug(title)
    validate_safe_slug(slug)

    iso_now = datetime.now(timezone.utc).isoformat()
    admin_email = user.get("email", "admin@charusat.ac.in")

    front_matter = (
        f"---\n"
        f"title: \"{title}\"\n"
        f"source_file: \"{draft['filename']}\"\n"
        f"uploaded_by: \"{admin_email}\"\n"
        f"uploaded_at: \"{iso_now}\"\n"
        f"programme: \"{programme}\"\n"
        f"source_note: \"{source_note}\"\n"
        f"kind: upload\n"
        f"---\n\n"
    )

    full_content = front_matter + draft["markdown"].strip() + "\n"
    target_local_path = UPLOADS_DIR / f"{slug}.md"
    target_local_path.write_text(full_content, encoding="utf-8")

    orig_ext = draft.get("extension", "bin")
    if draft.get("original_bytes"):
        orig_target = UPLOADS_ORIGINALS_DIR / f"{slug}.{orig_ext}"
        orig_target.write_bytes(draft["original_bytes"])

    gh = GitHubClient()
    is_gh_configured, missing = gh.is_configured()
    github_committed = False
    workflow_triggered = False
    message = "Saved to local knowledge base repository."

    if is_gh_configured:
        repo_rel_path = f"backend/knowledge_base/uploads/{slug}.md"
        commit_msg = f"kb: add {title} (via admin)"
        gh.commit_file(repo_rel_path, full_content.encode("utf-8"), commit_msg)
        github_committed = True

        if draft.get("original_bytes"):
            orig_repo_path = f"backend/knowledge_base/uploads/originals/{slug}.{orig_ext}"
            try:
                gh.commit_file(orig_repo_path, draft["original_bytes"], f"kb: add original for {title}")
            except Exception as e:
                logger.warning("Could not commit original file to GitHub: %s", e)

        try:
            gh.trigger_workflow(force_rebuild=True)
            workflow_triggered = True
            message = "Document published to repository. Rebuild workflow dispatched."
        except Exception as exc:
            logger.warning("Workflow dispatch failed: %s", exc)
            message = "Document published to repository. Could not trigger automatic rebuild."
    else:
        message = "Saved to local knowledge base only. GitHub integration not configured (missing: " + ", ".join(missing) + "). Rebuild vector database manually to index."

    db = get_db()
    log_audit_event(
        db,
        user,
        "kb_publish",
        "document",
        slug,
        {"title": title, "slug": slug, "github": github_committed},
    )

    return {
        "status": "success",
        "slug": slug,
        "title": title,
        "rel_path": f"uploads/{slug}.md",
        "github_committed": github_committed,
        "workflow_triggered": workflow_triggered,
        "message": message,
    }


@router.get("/kb/status")
async def kb_status(user: Dict[str, Any] = Depends(require_admin)):
    """Return knowledge base inventory, document statuses and sync automation info."""
    from app.kb_manager import get_kb_inventory, GitHubClient
    from app.embeddings import EmbeddingStore

    vector_store = None
    try:
        vector_store = EmbeddingStore().load_vector_store()
    except Exception:
        pass

    return get_kb_inventory(vector_store, GitHubClient())


@router.post("/kb/sync")
async def kb_sync(
    force_rebuild: bool = Query(False),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Trigger the knowledge base sync and rebuild GitHub Actions workflow."""
    from app.kb_manager import GitHubClient

    gh = GitHubClient()
    is_gh_configured, missing = gh.is_configured()
    if not is_gh_configured:
        raise HTTPException(
            status_code=400,
            detail=f"GitHub integration not configured. Missing variables: {', '.join(missing)}",
        )

    gh.trigger_workflow(force_rebuild=force_rebuild)
    db = get_db()
    log_audit_event(
        db,
        user,
        "kb_sync",
        "workflow",
        "sync-knowledge-base.yml",
        {"force_rebuild": force_rebuild},
    )
    return {"status": "success", "message": "Knowledge base sync workflow triggered successfully"}


@router.post("/kb/test-question")
async def kb_test_question(
    body: TestQuestionRequest,
    request: Request,
    user: Dict[str, Any] = Depends(require_admin),
):
    """Dry run test question against RAG retriever without logging or caching."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{user.get('email', 'admin')}_{client_ip}"
    _check_kb_test_rate_limit(rate_key)

    from app.embeddings import EmbeddingStore
    from app.retriever import RAGRetriever
    from app import config

    try:
        vector_store = EmbeddingStore().load_vector_store()
        retriever = RAGRetriever(vector_store)
        try:
            from app.conversation import analyze_turn
            plan = analyze_turn(body.question, history=[])
            standalone = getattr(plan, "standalone_question", body.question)
            chunks = retriever.retrieve(standalone, plan=plan)
        except Exception:
            standalone = body.question
            chunks = retriever.retrieve(body.question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retrieval dry-run failed: {exc}")

    results = []
    max_score = 0.0
    for doc, score in chunks:
        meta = doc.metadata or {}
        max_score = max(max_score, score)
        results.append({
            "source": meta.get("source", "unknown"),
            "title": meta.get("page_title", Path(meta.get("source", "")).stem),
            "programme": meta.get("program_name", "General"),
            "content_snippet": doc.page_content.strip()[:260],
            "score": round(score, 3),
        })

    answerable = max_score >= config.MIN_RELEVANCE_SCORE
    return {
        "question": body.question,
        "standalone_question": standalone,
        "answerable": answerable,
        "relevance_score": round(max_score, 3),
        "min_relevance_score": config.MIN_RELEVANCE_SCORE,
        "chunks": results,
    }


@router.delete("/kb/documents/{slug}")
async def kb_delete_document(
    slug: str,
    user: Dict[str, Any] = Depends(require_admin),
):
    """Delete an uploaded document. Rejects website or manual core documents."""
    from app.kb_manager import (
        validate_safe_slug,
        GitHubClient,
        UPLOADS_DIR,
        UPLOADS_ORIGINALS_DIR,
    )

    clean_slug = validate_safe_slug(slug)

    local_md = UPLOADS_DIR / f"{clean_slug}.md"
    if not local_md.exists():
        raise HTTPException(status_code=404, detail=f"Uploaded document '{clean_slug}' not found")

    try:
        local_md.unlink(missing_ok=True)
        for orig in UPLOADS_ORIGINALS_DIR.glob(f"{clean_slug}.*"):
            orig.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Failed to remove local file: %s", exc)

    gh = GitHubClient()
    if gh.is_configured()[0]:
        try:
            gh.delete_file(f"backend/knowledge_base/uploads/{clean_slug}.md", f"kb: delete {clean_slug} (via admin)")
            for ext in ("pdf", "docx", "md", "txt"):
                gh.delete_file(f"backend/knowledge_base/uploads/originals/{clean_slug}.{ext}", f"kb: delete original for {clean_slug}")
        except Exception as exc:
            logger.warning("GitHub deletion failed: %s", exc)

    db = get_db()
    log_audit_event(db, user, "kb_delete", "document", clean_slug, {"slug": clean_slug})
    return {"status": "success", "message": f"Document '{clean_slug}' deleted successfully"}


@router.post("/kb/faq")
async def kb_create_faq(
    body: FaqAnswerRequest,
    user: Dict[str, Any] = Depends(require_admin),
):
    """Save an answered knowledge gap as an FAQ document in uploads/ and resolve the gap."""
    from app.kb_manager import (
        generate_safe_slug,
        validate_safe_slug,
        GitHubClient,
        UPLOADS_DIR,
        ensure_upload_dirs,
    )

    ensure_upload_dirs()

    if len(body.answer.strip()) < 20:
        raise HTTPException(status_code=400, detail="Answer must be at least 20 characters long")
    if not body.source.strip():
        raise HTTPException(status_code=400, detail="Official source URL or document name is required")

    question_clean = body.question.strip()
    slug_base = generate_safe_slug(question_clean)
    slug = f"faq-{slug_base}"
    validate_safe_slug(slug)

    iso_now = datetime.now(timezone.utc).isoformat()
    admin_email = user.get("email", "admin@charusat.ac.in")
    programme = (body.programme or "GENERAL").strip().upper()

    faq_md = (
        f"---\n"
        f"title: \"FAQ: {question_clean}\"\n"
        f"kind: faq\n"
        f"question: \"{question_clean}\"\n"
        f"source: \"{body.source.strip()}\"\n"
        f"programme: \"{programme}\"\n"
        f"uploaded_by: \"{admin_email}\"\n"
        f"uploaded_at: \"{iso_now}\"\n"
        f"---\n\n"
        f"## Question\n\n"
        f"{question_clean}\n\n"
        f"## Answer\n\n"
        f"{body.answer.strip()}\n\n"
        f"## Source\n\n"
        f"{body.source.strip()}\n"
    )

    local_path = UPLOADS_DIR / f"{slug}.md"
    local_path.write_text(faq_md, encoding="utf-8")

    gh = GitHubClient()
    if gh.is_configured()[0]:
        try:
            gh.commit_file(
                f"backend/knowledge_base/uploads/{slug}.md",
                faq_md.encode("utf-8"),
                f"kb: add FAQ {slug} (via admin)",
            )
            gh.trigger_workflow(force_rebuild=True)
        except Exception as exc:
            logger.warning("GitHub sync failed for FAQ: %s", exc)

    db = get_db()
    if db is not None:
        try:
            gaps_coll = db["knowledge_gaps"]
            if body.gap_id:
                try:
                    gaps_coll.update_one(
                        {"_id": ObjectId(body.gap_id)},
                        {"$set": {"status": "resolved", "notes": f"Answered via FAQ uploads/{slug}.md", "updated_at": iso_now}},
                    )
                except Exception:
                    gaps_coll.update_one(
                        {"id": body.gap_id},
                        {"$set": {"status": "resolved", "notes": f"Answered via FAQ uploads/{slug}.md", "updated_at": iso_now}},
                    )
            else:
                gaps_coll.update_many(
                    {"normalized_question": question_clean.lower().strip()},
                    {"$set": {"status": "resolved", "notes": f"Answered via FAQ uploads/{slug}.md", "updated_at": iso_now}},
                )
        except Exception as exc:
            logger.warning("Failed to resolve knowledge gap: %s", exc)

    log_audit_event(
        db,
        user,
        "kb_publish",
        "faq",
        slug,
        {"question": question_clean, "slug": slug},
    )

    return {
        "status": "success",
        "slug": slug,
        "rel_path": f"uploads/{slug}.md",
        "message": "FAQ document created and knowledge gap resolved.",
    }
