"""Tests for the query resolver module.

Verifies that follow-up detection heuristics work correctly and that the
resolver produces sensible standalone queries.  These tests do NOT require
a live LLM or vector store.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.query_resolver import needs_resolution, resolve_followup_query, _heuristic_resolve


# -----------------------------------------------------------------------
# Heuristic: needs_resolution
# -----------------------------------------------------------------------

class TestNeedsResolution:
    def test_standalone_question_no_history(self) -> None:
        """A clear question with no history should not need resolution."""
        assert needs_resolution("What is the Online BCA fee?", []) is False

    def test_standalone_question_with_programme(self) -> None:
        """A self-contained question mentioning a programme is fine."""
        history = [
            {"role": "user", "content": "What is Online MBA fee?"},
            {"role": "assistant", "content": "The fee is ₹1,50,000."},
        ]
        assert needs_resolution("What is the Online BCA fee?", history) is False

    def test_followup_with_what_about(self) -> None:
        history = [
            {"role": "user", "content": "What is Online MBA fee?"},
            {"role": "assistant", "content": "The fee is ₹1,50,000."},
        ]
        assert needs_resolution("What about the duration?", history) is True

    def test_followup_with_anaphora_it(self) -> None:
        history = [
            {"role": "user", "content": "Tell me about Online BCA."},
            {"role": "assistant", "content": "Online BCA is a 3-year programme."},
        ]
        assert needs_resolution("What is it about?", history) is True

    def test_followup_with_anaphora_that(self) -> None:
        history = [
            {"role": "user", "content": "What is the MBA fee?"},
            {"role": "assistant", "content": "₹1,50,000."},
        ]
        assert needs_resolution("Is that per year or total?", history) is True

    def test_short_question_is_followup(self) -> None:
        """Very short questions (≤3 words) are treated as follow-ups."""
        history = [
            {"role": "user", "content": "Tell me about Online MBA."},
            {"role": "assistant", "content": "Online MBA is a 2-year programme."},
        ]
        assert needs_resolution("The fee?", history) is True
        assert needs_resolution("Duration?", history) is True

    def test_no_programme_in_question_but_in_history(self) -> None:
        """Question lacks programme name but history has one → follow-up."""
        history = [
            {"role": "user", "content": "What is the Online MBA fee?"},
            {"role": "assistant", "content": "The fee is ₹1,50,000."},
        ]
        assert needs_resolution("What is the examination fee?", history) is True

    def test_empty_history_always_false(self) -> None:
        assert needs_resolution("What about the fee?", []) is False


# -----------------------------------------------------------------------
# Heuristic fallback resolve
# -----------------------------------------------------------------------

class TestHeuristicResolve:
    def test_injects_programme_name(self) -> None:
        history = [
            {"role": "user", "content": "What is Online MBA fee?"},
            {"role": "assistant", "content": "₹1,50,000."},
        ]
        result = _heuristic_resolve("What is the examination fee?", history)
        assert "MBA" in result
        assert "examination fee" in result

    def test_no_injection_when_programme_present(self) -> None:
        history = [
            {"role": "user", "content": "What is Online MBA fee?"},
        ]
        result = _heuristic_resolve("What is Online BCA fee?", history)
        assert result == "What is Online BCA fee?"

    def test_no_injection_without_programme_in_history(self) -> None:
        history = [
            {"role": "user", "content": "What is the refund policy?"},
        ]
        result = _heuristic_resolve("What about the duration?", history)
        assert result == "What about the duration?"


# -----------------------------------------------------------------------
# Full resolve_followup_query (without LLM)
# -----------------------------------------------------------------------

class TestResolveFollowupQuery:
    def test_standalone_question_passes_through(self) -> None:
        result = resolve_followup_query("What is Online BCA fee?", [])
        assert result == "What is Online BCA fee?"

    def test_followup_resolved_heuristically_without_llm(self) -> None:
        history = [
            {"role": "user", "content": "What is the Online MBA fee?"},
            {"role": "assistant", "content": "₹1,50,000."},
        ]
        result = resolve_followup_query(
            "What about the examination fee?", history, llm_client=None,
        )
        # Should inject MBA context via heuristic
        assert "MBA" in result

    def test_self_contained_with_history_unchanged(self) -> None:
        """A question with its own programme name should not be rewritten."""
        history = [
            {"role": "user", "content": "What is the Online MBA fee?"},
            {"role": "assistant", "content": "₹1,50,000."},
        ]
        result = resolve_followup_query(
            "What is the Online BCA eligibility?", history, llm_client=None,
        )
        assert result == "What is the Online BCA eligibility?"
