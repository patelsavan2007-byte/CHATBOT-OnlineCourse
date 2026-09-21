"""Admin API routes.

Basic admin endpoints for future expansion. All endpoints require admin role.

Endpoints:
  GET /api/admin/stats — basic system statistics
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.auth import require_admin
from app.database import get_db
from app.models import get_conversation_count, get_user_count

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def admin_stats(user: Dict[str, Any] = Depends(require_admin)):
    """Get basic system statistics. Admin only."""
    db = get_db()
    stats = {
        "users": 0,
        "conversations": 0,
        "database_connected": db is not None,
    }

    if db is not None:
        try:
            stats["users"] = get_user_count(db)
            stats["conversations"] = get_conversation_count(db)
        except Exception:
            pass

    # RAG pipeline status
    import sys
    api_module = sys.modules.get("api")
    stats["rag_ready"] = getattr(api_module, "_rag_ready", False) if api_module else False

    return stats
