"""Tests for /api/suggest endpoint and suggestion service."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient

from api import app
from app import suggest_service
from app.suggest_service import (
    _assign_topic,
    _gate_answerability,
    _is_gap_match,
    _parse_and_sanitize,
    check_rate_limit,
    clear_rate_limits,
    clear_server_cache,
    generate_suggestions,
)


@pytest.fixture(autouse=True)
def reset_state():
    clear_rate_limits()
    clear_server_cache()
    yield
    clear_rate_limits()
    clear_server_cache()


def test_input_validation():
    """Inputs < 2 or > 100 characters must return an empty list immediately."""
    client = TestClient(app)

    # 1 character
    res = client.post("/api/suggest", json={"text": "w"})
    assert res.status_code == 200
    assert res.json() == {"suggestions": []}

    # whitespace only
    res = client.post("/api/suggest", json={"text": "   "})
    assert res.status_code == 200
    assert res.json() == {"suggestions": []}

    # > 100 characters
    res = client.post("/api/suggest", json={"text": "a" * 101})
    assert res.status_code == 422 or res.json() == {"suggestions": []}


def test_sanitize_and_filter_rules():
    """Ensure strict validation: drops > 110 chars, URLs, 4+ digits, exact matches, duplicates."""
    typed = "what are"
    raw_json = """{
        "suggestions": [
            "What are the fees for BCA?",
            "What are the fees for BCA?",
            "what are",
            "What are fees? Check https://charusat.online/fees",
            "What about the 20261 batch syllabus?",
            "What are the admission requirements for international students and who is the primary contact officer in charge of global affairs?",
            "What are the eligibility criteria for Online MCA"
        ]
    }"""
    filtered = _parse_and_sanitize(raw_json, typed)

    # 1. Duplicates: only one "What are the fees for BCA?"
    assert filtered.count("What are the fees for BCA?") == 1

    # 2. Equal to typed: "what are" dropped
    assert "what are" not in filtered
    assert "what are?" not in filtered

    # 3. URL dropped
    assert not any("https" in s for s in filtered)

    # 4. 4+ digits dropped ("20261")
    assert not any("20261" in s for s in filtered)

    # 5. Over 110 characters dropped
    assert not any(len(s) > 110 for s in filtered)

    # 6. Missing question mark added
    assert "What are the eligibility criteria for Online MCA?" in filtered


def test_rate_limiting():
    """Rate limit enforces 10 req/min for guests and 20 req/min for auth users."""
    clear_rate_limits()

    # Guest client: limit 10
    guest_ip = "192.168.1.10"
    for i in range(10):
        assert check_rate_limit(guest_ip, is_authenticated=False) is True
    # 11th request rejected
    assert check_rate_limit(guest_ip, is_authenticated=False) is False

    # Authenticated client: limit 20
    auth_user = "user_123"
    for i in range(20):
        assert check_rate_limit(auth_user, is_authenticated=True) is True
    # 21st request rejected
    assert check_rate_limit(auth_user, is_authenticated=True) is False


def test_server_caching():
    """Repeated calls within 5 minutes must return cached suggestions without calling LLM."""
    client = TestClient(app)

    with patch("app.suggest_service.call_groq_suggest", new=AsyncMock(return_value='{"suggestions": ["Which programmes are offered?"]}')) as mock_groq:
        res1 = client.post("/api/suggest", json={"text": "which prog"})
        assert res1.status_code == 200
        assert mock_groq.call_count == 1

        # Second call should hit the 5-minute cache
        res2 = client.post("/api/suggest", json={"text": "which prog"})
        assert res2.status_code == 200
        assert mock_groq.call_count == 1
        assert res1.json() == res2.json()


def test_gemini_fallback_when_groq_fails():
    """If Groq fails or times out, fall back to Gemini."""
    client = TestClient(app)

    with patch("app.suggest_service.call_groq_suggest", new=AsyncMock(return_value=None)), \
         patch("app.suggest_service.call_gemini_suggest", new=AsyncMock(return_value='{"suggestions": ["What is the eligibility criteria for Online MCA?"]}')) as mock_gemini:
        res = client.post("/api/suggest", json={"text": "mca eligibility"})
        assert res.status_code == 200
        assert mock_gemini.call_count == 1
        assert any("eligibility criteria for Online MCA" in s["text"] for s in res.json()["suggestions"])


def test_degraded_mode_when_both_fail():
    """When both LLMs fail, return nearest question bank candidates by embedding similarity."""
    client = TestClient(app)

    with patch("app.suggest_service.call_groq_suggest", new=AsyncMock(return_value=None)), \
         patch("app.suggest_service.call_gemini_suggest", new=AsyncMock(return_value=None)):
        res = client.post("/api/suggest", json={"text": "fee structure"})
        assert res.status_code == 200
        suggestions = res.json()["suggestions"]
        assert len(suggestions) > 0
        # Check that suggestions have text and topic
        assert all("text" in s and "topic" in s for s in suggestions)
        assert any("fee" in s["text"].lower() for s in suggestions)


def test_knowledge_gap_filtering():
    """Gated suggestions must filter out known knowledge gaps from chat_events."""
    known_gaps = {"what is the hostel fee"}
    assert _is_gap_match("What is the hostel fee?", known_gaps) is True
    assert _is_gap_match("What is the tuition fee?", known_gaps) is False


def test_answerability_gate():
    """Answerability gate drops candidates that score below MIN_RELEVANCE_SCORE."""
    import asyncio

    async def _run():
        mock_retriever = MagicMock()
        # First candidate scores high (0.75), second scores below threshold (0.40)
        mock_retriever.retrieve.side_effect = [
            [(MagicMock(), 0.75)],
            [(MagicMock(), 0.40)],
        ]

        passing = await _gate_answerability(
            mock_retriever,
            ["High relevance question?", "Low relevance question?"],
            budget=0.4,
        )
        assert len(passing) == 1
        assert passing[0] == "High relevance question?"

    asyncio.run(_run())


def test_privacy_logging(caplog):
    """Latency and provider are logged, NEVER the user's typed text."""
    client = TestClient(app)
    secret_text = "secret_unique_typed_string_xyz"

    with caplog.at_level(logging.INFO):
        client.post("/api/suggest", json={"text": secret_text})

    # Ensure secret text was never logged
    for record in caplog.records:
        assert secret_text not in record.message
        if "[SUGGEST]" in record.message:
            assert "provider=" in record.message
            assert "latency=" in record.message
            assert "count=" in record.message
