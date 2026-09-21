"""Data models and helper functions for MongoDB collections.

Collections:
  - users        : User accounts (email/password or Google OAuth)
  - conversations: Chat conversations scoped to a user
  - messages     : Individual chat messages within a conversation

All functions accept a ``pymongo.database.Database`` argument so they remain
testable and do not depend on global state.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo.database import Database

from app.utils import logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _oid(id_val: str | ObjectId) -> ObjectId:
    """Coerce a string into an ObjectId."""
    if isinstance(id_val, ObjectId):
        return id_val
    return ObjectId(id_val)


def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert a MongoDB document to a JSON-safe dict (ObjectId → str)."""
    if doc is None:
        return None
    result = dict(doc)
    if "_id" in result:
        result["id"] = str(result.pop("_id"))
    # Convert ObjectId fields
    for key, val in result.items():
        if isinstance(val, ObjectId):
            result[key] = str(val)
        elif isinstance(val, datetime):
            result[key] = val.isoformat()
    return result


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def create_user(
    db: Database,
    *,
    name: str,
    email: str,
    password_hash: Optional[str] = None,
    google_id: Optional[str] = None,
    avatar: Optional[str] = None,
    role: str = "user",
) -> Dict[str, Any]:
    """Insert a new user document. Returns the serialized user."""
    now = _now()
    doc = {
        "name": name,
        "email": email.lower().strip(),
        "password_hash": password_hash,
        "google_id": google_id,
        "avatar": avatar,
        "role": role,
        "created_at": now,
        "updated_at": now,
    }
    result = db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    logger.info("Created user: email=%s, role=%s", email, role)
    return serialize_doc(doc)


def find_user_by_email(db: Database, email: str) -> Optional[Dict[str, Any]]:
    """Find a user by email (case-insensitive)."""
    doc = db.users.find_one({"email": email.lower().strip()})
    return serialize_doc(doc)


def find_user_by_id(db: Database, user_id: str) -> Optional[Dict[str, Any]]:
    """Find a user by _id."""
    try:
        doc = db.users.find_one({"_id": _oid(user_id)})
        return serialize_doc(doc)
    except Exception:
        return None


def find_user_by_google_id(db: Database, google_id: str) -> Optional[Dict[str, Any]]:
    """Find a user by Google ID."""
    doc = db.users.find_one({"google_id": google_id})
    return serialize_doc(doc)


def update_user(db: Database, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update user fields. Returns the updated user."""
    updates["updated_at"] = _now()
    db.users.update_one({"_id": _oid(user_id)}, {"$set": updates})
    return find_user_by_id(db, user_id)


def get_user_count(db: Database) -> int:
    """Return total user count."""
    return db.users.count_documents({})


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

def create_conversation(
    db: Database,
    *,
    user_id: str,
    title: str = "New Chat",
) -> Dict[str, Any]:
    """Create a new conversation for a user."""
    now = _now()
    doc = {
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
    }
    result = db.conversations.insert_one(doc)
    doc["_id"] = result.inserted_id
    logger.info("Created conversation: user_id=%s, title=%r", user_id, title)
    return serialize_doc(doc)


def get_user_conversations(db: Database, user_id: str) -> List[Dict[str, Any]]:
    """Return all conversations for a user, newest first."""
    cursor = db.conversations.find(
        {"user_id": user_id}
    ).sort("updated_at", -1)
    return [serialize_doc(doc) for doc in cursor]


def get_conversation(db: Database, conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a single conversation, verifying it belongs to the user."""
    try:
        doc = db.conversations.find_one({
            "_id": _oid(conversation_id),
            "user_id": user_id,
        })
        return serialize_doc(doc)
    except Exception:
        return None


def update_conversation(
    db: Database,
    conversation_id: str,
    user_id: str,
    updates: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Update a conversation (e.g. rename). Returns the updated doc."""
    updates["updated_at"] = _now()
    result = db.conversations.update_one(
        {"_id": _oid(conversation_id), "user_id": user_id},
        {"$set": updates},
    )
    if result.matched_count == 0:
        return None
    return get_conversation(db, conversation_id, user_id)


def delete_conversation(db: Database, conversation_id: str, user_id: str) -> bool:
    """Delete a conversation and all its messages. Returns True if deleted."""
    try:
        oid = _oid(conversation_id)
        # Verify ownership
        conv = db.conversations.find_one({"_id": oid, "user_id": user_id})
        if not conv:
            return False
        # Delete messages first
        db.messages.delete_many({"conversation_id": conversation_id})
        # Delete conversation
        db.conversations.delete_one({"_id": oid})
        logger.info("Deleted conversation: %s", conversation_id)
        return True
    except Exception as exc:
        logger.error("Failed to delete conversation %s: %s", conversation_id, exc)
        return False


def get_conversation_count(db: Database) -> int:
    """Return total conversation count."""
    return db.conversations.count_documents({})


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def create_message(
    db: Database,
    *,
    conversation_id: str,
    role: str,
    content: str,
    sources: Optional[List[Dict[str, Any]]] = None,
    suggested_questions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Insert a message into a conversation."""
    now = _now()
    doc = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "sources": sources or [],
        "suggested_questions": suggested_questions or [],
        "created_at": now,
    }
    result = db.messages.insert_one(doc)
    doc["_id"] = result.inserted_id

    # Update the conversation's updated_at timestamp
    try:
        db.conversations.update_one(
            {"_id": _oid(conversation_id)},
            {"$set": {"updated_at": now}},
        )
    except Exception:
        pass

    return serialize_doc(doc)


def get_conversation_messages(
    db: Database,
    conversation_id: str,
) -> List[Dict[str, Any]]:
    """Return all messages in a conversation, oldest first."""
    cursor = db.messages.find(
        {"conversation_id": conversation_id}
    ).sort("created_at", 1)
    return [serialize_doc(doc) for doc in cursor]


def generate_conversation_title(question: str) -> str:
    """Generate a short title from the first user question."""
    # Remove common question prefixes
    clean = question.strip()
    # Truncate to a reasonable title length
    if len(clean) > 60:
        # Try to break at a word boundary
        truncated = clean[:57]
        last_space = truncated.rfind(" ")
        if last_space > 30:
            truncated = truncated[:last_space]
        clean = truncated + "..."
    return clean or "New Chat"
