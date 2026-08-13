"""MongoDB client singleton for SkillForge AI.

Provides a shared database connection used by all career-related
endpoints.  Falls back gracefully if MongoDB is unavailable — the
pipeline can still generate plans, they just won't be persisted.

Collections
-----------
- ``career_analyses``  : saved analysis results (profile + skill gap)
- ``career_plans``     : saved personalized career plans
"""
from __future__ import annotations

import os
from typing import Optional

from app.utils import logger, print_info, print_warning

try:
    from pymongo import MongoClient
    from pymongo.database import Database
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    HAS_PYMONGO = True
except ImportError:
    MongoClient = None  # type: ignore[assignment,misc]
    Database = None  # type: ignore[assignment,misc]
    HAS_PYMONGO = False


_client: Optional[MongoClient] = None  # type: ignore[assignment]
_db: Optional[Database] = None  # type: ignore[assignment]


def get_db() -> Optional[Database]:  # type: ignore[return]
    """Return the MongoDB database instance, or ``None`` if unavailable.

    On first call, initialises the client and verifies the connection.
    Subsequent calls return the cached database object.
    """
    global _client, _db

    if _db is not None:
        return _db

    if not HAS_PYMONGO:
        print_warning("[MongoDB] pymongo is not installed. Data will NOT be persisted.")
        logger.warning("pymongo not installed — skipping MongoDB")
        return None

    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "skillforge")

    try:
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Verify connection
        _client.admin.command("ping")
        _db = _client[db_name]

        # Create indexes for user isolation
        _db["career_analyses"].create_index("user_id")
        _db["career_analyses"].create_index("analysis_id", unique=True)
        _db["career_plans"].create_index("user_id")
        _db["career_plans"].create_index("plan_id", unique=True)

        print_info(f"[MongoDB] Connected to '{db_name}' at {uri[:40]}...")
        logger.info("MongoDB connected: db=%s", db_name)
        return _db

    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        print_warning(f"[MongoDB] Connection failed: {exc}. Data will NOT be persisted.")
        logger.warning("MongoDB connection failed: %s", exc)
        _client = None
        _db = None
        return None
    except Exception as exc:
        print_warning(f"[MongoDB] Unexpected error: {exc}. Data will NOT be persisted.")
        logger.error("MongoDB unexpected error: %s", exc)
        _client = None
        _db = None
        return None


def save_analysis(data: dict) -> bool:
    """Save an analysis result to MongoDB. Returns True on success."""
    db = get_db()
    if db is None:
        return False
    try:
        db["career_analyses"].replace_one(
            {"analysis_id": data["analysis_id"]},
            data,
            upsert=True,
        )
        return True
    except Exception as exc:
        logger.error("Failed to save analysis: %s", exc)
        return False


def get_analysis(analysis_id: str, user_id: str) -> Optional[dict]:
    """Retrieve an analysis by ID, scoped to the user."""
    db = get_db()
    if db is None:
        return None
    try:
        return db["career_analyses"].find_one(
            {"analysis_id": analysis_id, "user_id": user_id},
            {"_id": 0},
        )
    except Exception as exc:
        logger.error("Failed to fetch analysis: %s", exc)
        return None


def get_latest_analysis(user_id: str) -> Optional[dict]:
    """Retrieve the most recent analysis for a user."""
    db = get_db()
    if db is None:
        return None
    try:
        return db["career_analyses"].find_one(
            {"user_id": user_id},
            {"_id": 0},
            sort=[("created_at", -1)],
        )
    except Exception as exc:
        logger.error("Failed to fetch latest analysis: %s", exc)
        return None


def save_plan(data: dict) -> bool:
    """Save a career plan to MongoDB. Returns True on success."""
    db = get_db()
    if db is None:
        return False
    try:
        db["career_plans"].replace_one(
            {"plan_id": data["plan_id"]},
            data,
            upsert=True,
        )
        return True
    except Exception as exc:
        logger.error("Failed to save plan: %s", exc)
        return False


def get_plan(plan_id: str, user_id: str) -> Optional[dict]:
    """Retrieve a plan by ID, scoped to the user."""
    db = get_db()
    if db is None:
        return None
    try:
        return db["career_plans"].find_one(
            {"plan_id": plan_id, "user_id": user_id},
            {"_id": 0},
        )
    except Exception as exc:
        logger.error("Failed to fetch plan: %s", exc)
        return None


def get_latest_plan(user_id: str) -> Optional[dict]:
    """Retrieve the most recent plan for a user."""
    db = get_db()
    if db is None:
        return None
    try:
        return db["career_plans"].find_one(
            {"user_id": user_id},
            {"_id": 0},
            sort=[("created_at", -1)],
        )
    except Exception as exc:
        logger.error("Failed to fetch latest plan: %s", exc)
        return None
