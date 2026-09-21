"""MongoDB connection module for the CHARUSAT Online Course Assistant.

Provides synchronous MongoDB access using pymongo, matching the existing
FastAPI sync handler patterns used throughout the backend.

When MONGODB_URI is not configured, all database operations gracefully
return None / empty results so the RAG chatbot continues to work without
persistence.
"""
from __future__ import annotations

import os
from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.utils import logger, print_info, print_warning

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_client: Optional[MongoClient] = None
_db: Optional[Database] = None

DB_NAME = "charusat_assistant"


def init_mongodb() -> Optional[Database]:
    """Initialise the MongoDB connection from MONGODB_URI env var.

    Returns the Database object on success, or None if the URI is missing
    or the connection cannot be established.  Safe to call multiple times
    (idempotent).
    """
    global _client, _db

    if _db is not None:
        return _db

    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        print_warning("MONGODB_URI not set — chat history and auth will be unavailable.")
        logger.warning("MONGODB_URI not configured; skipping MongoDB initialisation")
        return None

    try:
        _client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        # Verify connectivity
        _client.admin.command("ping")
        _db = _client[DB_NAME]
        _ensure_indexes(_db)
        print_info(f"MongoDB connected: {DB_NAME}")
        logger.info("MongoDB connected to database '%s'", DB_NAME)
        return _db
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        print_warning(f"MongoDB connection failed: {exc}")
        logger.error("MongoDB connection failed: %s", exc)
        _client = None
        _db = None
        return None
    except Exception as exc:
        print_warning(f"MongoDB initialisation error: {exc}")
        logger.error("MongoDB initialisation error: %s", exc)
        _client = None
        _db = None
        return None


def get_db() -> Optional[Database]:
    """Return the current MongoDB database reference, or None."""
    return _db


def close_mongodb() -> None:
    """Close the MongoDB connection if open."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


def _ensure_indexes(db: Database) -> None:
    """Create required indexes (idempotent)."""
    try:
        # Users — unique email
        db.users.create_index("email", unique=True)
        db.users.create_index("google_id", sparse=True)

        # Conversations — lookup by user, sorted by updated_at
        db.conversations.create_index([("user_id", 1), ("updated_at", -1)])

        # Messages — lookup by conversation, sorted by created_at
        db.messages.create_index([("conversation_id", 1), ("created_at", 1)])

        logger.info("MongoDB indexes ensured")
    except Exception as exc:
        logger.warning("Failed to create MongoDB indexes: %s", exc)
