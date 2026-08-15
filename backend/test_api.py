"""Integration tests for the FastAPI HTTP API.

Uses FastAPI's TestClient with mocked RAG components so no vector store,
LLM API key, or ChromaDB is needed to run these tests.

The mocking strategy avoids importing heavy dependencies (langchain_chroma,
sentence_transformers, etc.) by patching ``sys.modules`` and then replacing
the module-level objects in ``api.py`` after import.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# -----------------------------------------------------------------------
# Inject stub modules for heavy dependencies that may not be installed
# in the test environment.  This must happen BEFORE importing api.py.
# -----------------------------------------------------------------------

_STUB_MODULES = [
    "langchain_chroma",
    "langchain_core",
    "langchain_core.documents",
    "langchain_community",
    "langchain_google_genai",
    "langchain_huggingface",
    "langchain_openai",
    "langchain_text_splitters",
    "langchain",
    "sentence_transformers",
    "chromadb",
    "crawl4ai",
    "google.genai",
    "google.genai.types",
    "google",
    "groq",
    "pymupdf",
    "fitz",
    "pypdf",
    "tqdm",
    "lxml",
]

for _mod_name in _STUB_MODULES:
    if _mod_name not in sys.modules:
        try:
            __import__(_mod_name)
        except ImportError:
            sys.modules[_mod_name] = MagicMock()


def _make_mock_doc(content: str = "mock content", source: str = "mock.pdf", page: int = 1):
    """Create a mock Document-like object."""
    doc = MagicMock()
    doc.page_content = content
    doc.metadata = {"source": source, "page": page, "chunk_id": "c1", "content_type": "text"}
    return doc


# -----------------------------------------------------------------------
# Now we can safely import and set up the api module with mocked internals.
# -----------------------------------------------------------------------

# Prevent the real module-level initialisation in api.py by pre-patching
# the classes it uses.
import app.config as _config
_config.ensure_directories = lambda: None

# Create module-level mocks
_mock_vector_store = MagicMock()
_mock_vector_store._collection.count.return_value = 42

_mock_embedding_store = MagicMock()
_mock_embedding_store.load_vector_store.return_value = _mock_vector_store
_mock_embedding_store.persist_directory = "/fake"

# Patch EmbeddingStore before api.py imports it
import app.embeddings as _embeddings_mod
_embeddings_mod.EmbeddingStore = lambda: _mock_embedding_store

# Patch RAGRetriever
_mock_retriever = MagicMock()
_mock_retriever.retrieve.return_value = [(_make_mock_doc(), 0.85)]
_mock_retriever.last_program = "online_mba"
_mock_retriever.last_pool = [(_make_mock_doc(), 0.85)]

import app.retriever as _retriever_mod
_retriever_mod.RAGRetriever = lambda vs: _mock_retriever

# Patch LLMClient
_mock_llm = MagicMock()
_mock_llm.generate.return_value = ("The answer is 42.", "gemini")

import app.llm as _llm_mod
_llm_mod.LLMClient = lambda: _mock_llm

# Patch RAGChain
_mock_chain = MagicMock()
_mock_chain.last_status = "gemini"
_mock_chain.last_conflicts = []
_mock_chain.answer_with_history.return_value = (
    "The Online MBA fee is ₹1,50,000.",
    [(_make_mock_doc(source="PPR_Online_MBA.pdf"), 0.9)],
    "What is the Online MBA fee?",
)

import app.rag_chain as _rag_chain_mod
_rag_chain_mod.RAGChain = lambda r, l: _mock_chain

# NOW import the api module — it will use our patched classes.
import api as api_module
from fastapi.testclient import TestClient


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

@pytest.fixture
def client():
    """Return a TestClient with a fresh ConversationStore."""
    from app.conversation_history import ConversationStore
    api_module.conversation_store = ConversationStore()
    api_module.rag_chain = _mock_chain
    # Reset mock call history
    _mock_chain.reset_mock()
    _mock_chain.last_status = "gemini"
    _mock_chain.last_conflicts = []
    _mock_chain.answer_with_history.return_value = (
        "The Online MBA fee is ₹1,50,000.",
        [(_make_mock_doc(source="PPR_Online_MBA.pdf"), 0.9)],
        "What is the Online MBA fee?",
    )
    return TestClient(api_module.app)


# -----------------------------------------------------------------------
# 1. POST /chat without session_id
# -----------------------------------------------------------------------

class TestChatWithoutSession:
    def test_creates_new_session(self, client) -> None:
        response = client.post("/chat", json={"question": "What is Online MBA fee?"})
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0
        assert data["answer"]

    def test_does_not_expose_debug_fields(self, client) -> None:
        """The API payload only carries session_id and answer — no debug details."""
        response = client.post("/chat", json={"question": "What is Online MBA fee?"})
        data = response.json()
        assert set(data.keys()) == {"session_id", "answer"}
        for hidden in ("sources", "resolved_query", "llm_status", "scores", "chunks"):
            assert hidden not in data


# -----------------------------------------------------------------------
# 2. POST /chat with session_id — history grows
# -----------------------------------------------------------------------

class TestChatWithSession:
    def test_reuses_session(self, client) -> None:
        # First message
        r1 = client.post("/chat", json={"question": "What is Online MBA fee?"})
        session_id = r1.json()["session_id"]

        # Second message with same session
        r2 = client.post("/chat", json={
            "session_id": session_id,
            "question": "What about the duration?",
        })
        assert r2.status_code == 200
        assert r2.json()["session_id"] == session_id

    def test_history_grows_across_messages(self, client) -> None:
        r1 = client.post("/chat", json={"question": "First question"})
        session_id = r1.json()["session_id"]

        r2 = client.post("/chat", json={
            "session_id": session_id,
            "question": "Second question",
        })
        assert r2.status_code == 200

        # The mock chain should have been called with history on the second call
        assert _mock_chain.answer_with_history.call_count == 2
        # Second call should have received non-empty history
        second_call_history = _mock_chain.answer_with_history.call_args_list[1][0][1]
        assert len(second_call_history) == 2  # user + assistant from first turn


# -----------------------------------------------------------------------
# 3. DELETE /chat/history/{session_id}
# -----------------------------------------------------------------------

class TestClearHistory:
    def test_clear_existing_session(self, client) -> None:
        r1 = client.post("/chat", json={"question": "Hello"})
        session_id = r1.json()["session_id"]

        r2 = client.delete(f"/chat/history/{session_id}")
        assert r2.status_code == 200
        data = r2.json()
        assert data["session_id"] == session_id
        assert data["cleared"] is True

    def test_clear_nonexistent_session_returns_404(self, client) -> None:
        r = client.delete("/chat/history/nonexistent-session-id")
        assert r.status_code == 404


# -----------------------------------------------------------------------
# 4. Session isolation
# -----------------------------------------------------------------------

class TestSessionIsolation:
    def test_different_sessions_are_independent(self, client) -> None:
        r_a = client.post("/chat", json={"question": "Session A question"})
        sid_a = r_a.json()["session_id"]

        r_b = client.post("/chat", json={"question": "Session B question"})
        sid_b = r_b.json()["session_id"]

        assert sid_a != sid_b


# -----------------------------------------------------------------------
# 5. RAG chain is called correctly
# -----------------------------------------------------------------------

class TestRAGIntegration:
    def test_answer_with_history_is_called(self, client) -> None:
        """Verify the API uses answer_with_history."""
        response = client.post("/chat", json={"question": "Test question"})
        assert response.status_code == 200
        _mock_chain.answer_with_history.assert_called_once()

    def test_original_question_is_passed(self, client) -> None:
        """The original question (not resolved) should be passed."""
        client.post("/chat", json={"question": "My specific question"})
        call_args = _mock_chain.answer_with_history.call_args
        assert call_args[0][0] == "My specific question"


# -----------------------------------------------------------------------
# 6. Health check
# -----------------------------------------------------------------------

class TestHealthCheck:
    def test_health_returns_ok(self, client) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "vector_store_documents" in data


# -----------------------------------------------------------------------
# 7. Validation
# -----------------------------------------------------------------------

class TestValidation:
    def test_empty_question_rejected(self, client) -> None:
        r = client.post("/chat", json={"question": ""})
        assert r.status_code == 422  # Pydantic validation error

    def test_missing_question_rejected(self, client) -> None:
        r = client.post("/chat", json={})
        assert r.status_code == 422
