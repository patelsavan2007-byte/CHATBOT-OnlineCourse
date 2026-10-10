"""Admin API routes.

Basic admin endpoints for future expansion. All endpoints require admin role.

Endpoints:
  GET /api/admin/stats — basic system statistics
  GET /api/admin/cache — cache statistics
  DELETE /api/admin/cache — clear cache
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.auth import require_admin
from app.cache import get_cache
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

    # Cache statistics
    try:
        cache = get_cache()
        stats["cache"] = cache.get_stats()
    except Exception:
        stats["cache"] = {"error": "Cache not available"}

    return stats


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
