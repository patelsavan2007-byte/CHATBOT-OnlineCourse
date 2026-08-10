"""In-memory conversation history store.

This module manages chat session history for the CHARUSAT Online Course
Assistant.  Each conversation is identified by a UUID ``session_id``.

**Important limitations (by design at this stage):**

* **In-memory only** — all history is lost when the backend process restarts.
* **No authentication** — the ``session_id`` is the sole conversation
  identifier; there is no user account, login, or token.
* **No persistent storage** — there is no SQLite, PostgreSQL, MongoDB, or any
  other database behind this store.  A database layer can be added later
  without changing the public API of this module.
* **Session isolation** — different ``session_id`` values represent completely
  independent conversations.  History from one session is never visible to
  another.

The module is intentionally independent of ChromaDB, the vector store, and the
LLM client so it can be tested and used in isolation.
"""
from __future__ import annotations

import uuid
from threading import Lock
from typing import Dict, List, Optional

from app import config
from app.utils import logger


class ConversationStore:
    """Thread-safe in-memory store for conversation histories.

    Each session is a list of ``{"role": ..., "content": ...}`` dicts.

    .. note::
        Restarting the backend process clears **all** stored conversations.
        There is no persistent storage at this stage.
    """

    def __init__(self) -> None:
        self._store: Dict[str, List[Dict[str, str]]] = {}
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self) -> str:
        """Create a new empty session and return its UUID."""
        session_id = str(uuid.uuid4())
        with self._lock:
            self._store[session_id] = []
        logger.info("Created new conversation session: %s", session_id)
        return session_id

    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """Return *session_id* if it exists, otherwise create a new session.

        If *session_id* is ``None`` or empty, a brand-new session is created.
        If a non-``None`` value is given but does not exist in the store, it is
        created with an empty history so subsequent calls can append to it.
        """
        if not session_id:
            return self.create_session()
        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = []
                logger.info("Created session for provided ID: %s", session_id)
        return session_id

    def session_exists(self, session_id: str) -> bool:
        """Return ``True`` if *session_id* has been created."""
        with self._lock:
            return session_id in self._store

    def clear_session(self, session_id: str) -> bool:
        """Remove all messages for *session_id*.

        Returns ``True`` if the session existed (and was cleared), ``False`` if
        the session was not found.
        """
        with self._lock:
            if session_id in self._store:
                self._store[session_id] = []
                logger.info("Cleared conversation session: %s", session_id)
                return True
            return False

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to the session history.

        Parameters
        ----------
        session_id:
            Must refer to an existing session (see :meth:`get_or_create_session`).
        role:
            Either ``"user"`` or ``"assistant"``.
        content:
            The message text.
        """
        if role not in ("user", "assistant"):
            raise ValueError(f"role must be 'user' or 'assistant', got {role!r}")
        with self._lock:
            if session_id not in self._store:
                raise KeyError(f"Session {session_id!r} does not exist")
            self._store[session_id].append({"role": role, "content": content})

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Return the **full** message list for *session_id* (copy)."""
        with self._lock:
            messages = self._store.get(session_id)
            if messages is None:
                return []
            return list(messages)

    def get_recent_history(self, session_id: str) -> List[Dict[str, str]]:
        """Return the most recent messages, respecting the configured limit.

        The limit is ``config.CHAT_HISTORY_MAX_MESSAGES``.  Only the **last**
        N messages are returned so the LLM prompt stays bounded.
        """
        with self._lock:
            messages = self._store.get(session_id)
            if messages is None:
                return []
            limit = config.CHAT_HISTORY_MAX_MESSAGES
            if len(messages) <= limit:
                return list(messages)
            return list(messages[-limit:])
