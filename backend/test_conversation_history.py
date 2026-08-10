"""Unit tests for the ConversationStore.

These tests verify session creation, message management, history limits,
session isolation, and clearing — all without requiring ChromaDB, the
vector store, or any LLM API.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.conversation_history import ConversationStore


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

@pytest.fixture
def store() -> ConversationStore:
    """Return a fresh, empty ConversationStore for each test."""
    return ConversationStore()


# -----------------------------------------------------------------------
# 1. New session creation
# -----------------------------------------------------------------------

class TestSessionCreation:
    def test_create_session_returns_valid_uuid(self, store: ConversationStore) -> None:
        session_id = store.create_session()
        # Must be a valid UUID-4 string.
        parsed = uuid.UUID(session_id, version=4)
        assert str(parsed) == session_id

    def test_create_session_returns_unique_ids(self, store: ConversationStore) -> None:
        ids = {store.create_session() for _ in range(50)}
        assert len(ids) == 50

    def test_new_session_has_empty_history(self, store: ConversationStore) -> None:
        session_id = store.create_session()
        assert store.get_history(session_id) == []


# -----------------------------------------------------------------------
# 2. Adding user / assistant messages
# -----------------------------------------------------------------------

class TestAddMessage:
    def test_add_user_message(self, store: ConversationStore) -> None:
        sid = store.create_session()
        store.add_message(sid, "user", "Hello")
        history = store.get_history(sid)
        assert len(history) == 1
        assert history[0] == {"role": "user", "content": "Hello"}

    def test_add_assistant_message(self, store: ConversationStore) -> None:
        sid = store.create_session()
        store.add_message(sid, "assistant", "Hi there!")
        history = store.get_history(sid)
        assert len(history) == 1
        assert history[0] == {"role": "assistant", "content": "Hi there!"}

    def test_add_multiple_messages_preserves_order(self, store: ConversationStore) -> None:
        sid = store.create_session()
        store.add_message(sid, "user", "Q1")
        store.add_message(sid, "assistant", "A1")
        store.add_message(sid, "user", "Q2")
        history = store.get_history(sid)
        assert len(history) == 3
        assert [m["content"] for m in history] == ["Q1", "A1", "Q2"]

    def test_add_message_invalid_role_raises(self, store: ConversationStore) -> None:
        sid = store.create_session()
        with pytest.raises(ValueError, match="role must be"):
            store.add_message(sid, "system", "not allowed")

    def test_add_message_nonexistent_session_raises(self, store: ConversationStore) -> None:
        with pytest.raises(KeyError):
            store.add_message("nonexistent-id", "user", "Hello")


# -----------------------------------------------------------------------
# 3. Retrieving history
# -----------------------------------------------------------------------

class TestGetHistory:
    def test_get_history_returns_copy(self, store: ConversationStore) -> None:
        sid = store.create_session()
        store.add_message(sid, "user", "Hello")
        h1 = store.get_history(sid)
        h2 = store.get_history(sid)
        assert h1 == h2
        assert h1 is not h2  # different list objects

    def test_get_history_unknown_session_returns_empty(self, store: ConversationStore) -> None:
        assert store.get_history("does-not-exist") == []


# -----------------------------------------------------------------------
# 4. History limit
# -----------------------------------------------------------------------

class TestHistoryLimit:
    def test_get_recent_history_respects_limit(self, store: ConversationStore) -> None:
        sid = store.create_session()
        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            store.add_message(sid, role, f"Message {i}")

        with patch("app.config.CHAT_HISTORY_MAX_MESSAGES", 6):
            recent = store.get_recent_history(sid)

        assert len(recent) == 6
        # Should be the last 6 messages
        assert recent[0]["content"] == "Message 14"
        assert recent[-1]["content"] == "Message 19"

    def test_get_recent_history_under_limit_returns_all(self, store: ConversationStore) -> None:
        sid = store.create_session()
        store.add_message(sid, "user", "Q1")
        store.add_message(sid, "assistant", "A1")

        with patch("app.config.CHAT_HISTORY_MAX_MESSAGES", 10):
            recent = store.get_recent_history(sid)

        assert len(recent) == 2

    def test_get_recent_history_unknown_session_returns_empty(self, store: ConversationStore) -> None:
        assert store.get_recent_history("nonexistent") == []


# -----------------------------------------------------------------------
# 5. Session isolation
# -----------------------------------------------------------------------

class TestSessionIsolation:
    def test_sessions_are_isolated(self, store: ConversationStore) -> None:
        """Session A and Session B must never share history."""
        sid_a = store.create_session()
        sid_b = store.create_session()

        store.add_message(sid_a, "user", "What is Online MBA fee?")
        store.add_message(sid_a, "assistant", "The Online MBA fee is ₹1,50,000.")

        store.add_message(sid_b, "user", "What is Online BCA fee?")
        store.add_message(sid_b, "assistant", "The Online BCA fee is ₹60,000.")

        history_a = store.get_history(sid_a)
        history_b = store.get_history(sid_b)

        assert len(history_a) == 2
        assert len(history_b) == 2

        # Session A must only contain MBA-related messages
        assert "MBA" in history_a[0]["content"]
        assert "BCA" not in history_a[0]["content"]

        # Session B must only contain BCA-related messages
        assert "BCA" in history_b[0]["content"]
        assert "MBA" not in history_b[0]["content"]


# -----------------------------------------------------------------------
# 6. Clearing history
# -----------------------------------------------------------------------

class TestClearSession:
    def test_clear_existing_session(self, store: ConversationStore) -> None:
        sid = store.create_session()
        store.add_message(sid, "user", "Hello")
        assert len(store.get_history(sid)) == 1

        result = store.clear_session(sid)
        assert result is True
        assert store.get_history(sid) == []
        # Session should still exist after clearing
        assert store.session_exists(sid)

    def test_clear_nonexistent_session_returns_false(self, store: ConversationStore) -> None:
        result = store.clear_session("nonexistent")
        assert result is False


# -----------------------------------------------------------------------
# 7. Missing session_id creates a new session
# -----------------------------------------------------------------------

class TestGetOrCreateSession:
    def test_none_creates_new_session(self, store: ConversationStore) -> None:
        sid = store.get_or_create_session(None)
        assert store.session_exists(sid)
        uuid.UUID(sid, version=4)  # valid UUID

    def test_empty_string_creates_new_session(self, store: ConversationStore) -> None:
        sid = store.get_or_create_session("")
        assert store.session_exists(sid)

    def test_existing_id_is_reused(self, store: ConversationStore) -> None:
        original = store.create_session()
        returned = store.get_or_create_session(original)
        assert returned == original

    def test_unknown_id_is_created(self, store: ConversationStore) -> None:
        custom_id = "custom-session-id-123"
        returned = store.get_or_create_session(custom_id)
        assert returned == custom_id
        assert store.session_exists(custom_id)


# -----------------------------------------------------------------------
# 8. Session exists check
# -----------------------------------------------------------------------

class TestSessionExists:
    def test_exists_after_creation(self, store: ConversationStore) -> None:
        sid = store.create_session()
        assert store.session_exists(sid) is True

    def test_does_not_exist_before_creation(self, store: ConversationStore) -> None:
        assert store.session_exists("never-created") is False


# -----------------------------------------------------------------------
# 9. Empty history
# -----------------------------------------------------------------------

class TestEmptyHistory:
    def test_fresh_session_get_history(self, store: ConversationStore) -> None:
        sid = store.create_session()
        assert store.get_history(sid) == []

    def test_fresh_session_get_recent_history(self, store: ConversationStore) -> None:
        sid = store.create_session()
        assert store.get_recent_history(sid) == []


# -----------------------------------------------------------------------
# 10. Restart behaviour documentation
# -----------------------------------------------------------------------

class TestDocumentation:
    def test_module_documents_restart_behaviour(self) -> None:
        """Verify the module docstring documents that history is not persistent."""
        import app.conversation_history as mod
        docstring = mod.__doc__
        assert "in-memory" in docstring.lower()
        assert "restart" in docstring.lower() or "lost" in docstring.lower()

    def test_class_documents_restart_behaviour(self) -> None:
        docstring = ConversationStore.__doc__
        assert "restart" in docstring.lower() or "persistent" in docstring.lower()
