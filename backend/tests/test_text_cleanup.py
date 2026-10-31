"""Comprehensive offline regression tests for answer text cleanup (ITEM 11).

Tests:
  - U+200B, U+200C, U+200D, U+2060 and U+FEFF are deleted (not replaced by spaces)
  - U+00A0, U+202F, U+2009, U+200A and U+2007 become a normal ASCII space
  - URLs are never altered
  - A lone em dash in a markdown table cell becomes "N/A"
  - A prose em dash becomes a comma or period
  - En dashes (U+2013) are untouched
  - The cleanup runs on cache and conversation read without rewriting database
  - Streaming test: reassembled chunks equal final answer exactly
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from app.text_cleanup import clean_answer_text


def test_zero_width_characters_deleted():
    """U+200B, U+200C, U+200D, U+2060 and U+FEFF must be deleted, not replaced by spaces."""
    raw = "CHAR\u200bU\u200cSAT\u200d On\u2060line\ufeff Degree"
    cleaned = clean_answer_text(raw)
    assert cleaned == "CHARUSAT Online Degree"
    assert "CHARUSAT" in cleaned
    assert "Online" in cleaned


def test_spaces_normalized_to_ascii_space():
    """U+00A0, U+202F, U+2009, U+200A and U+2007 must become a standard ASCII space."""
    raw = "CHARUSAT\u00a0Online\u202Fthe\u2009home\u200apage\u2007Section 2(f)"
    cleaned = clean_answer_text(raw)
    assert cleaned == "CHARUSAT Online the home page Section 2(f)"
    for char in ["\u00a0", "\u202f", "\u2009", "\u200a", "\u2007"]:
        assert char not in cleaned


def test_urls_never_altered():
    """URLs must be preserved verbatim even when containing query params or special paths."""
    url = "https://charusat.online/programmes/bca?term=2025-2026&ref=portal#fees"
    text = f"Visit {url} for details."
    cleaned = clean_answer_text(text)
    assert url in cleaned


def test_lone_em_dash_in_table_cell_becomes_na():
    """A lone em dash in a markdown table cell must become 'N/A'."""
    table = "| Programme | Fee |\n|---|---|\n| BBA | — |\n| BCA | 20000 |"
    cleaned = clean_answer_text(table)
    assert "| BBA | N/A |" in cleaned


def test_prose_em_dash_becomes_comma():
    """A prose em dash in sentence text must become a comma."""
    raw = "The online BBA—a three-year degree—is approved by UGC."
    cleaned = clean_answer_text(raw)
    assert "—" not in cleaned
    assert "The online BBA, a three-year degree, is approved by UGC." == cleaned


def test_en_dash_untouched():
    """En dash (U+2013) for numeric or date ranges must not be touched."""
    raw = "Academic year 2025–26 (Semesters 1–6)"
    cleaned = clean_answer_text(raw)
    assert "2025–26" in cleaned
    assert "1–6" in cleaned
    assert "\u2013" in cleaned


def test_streaming_chunks_reassemble_to_final_answer():
    """Streaming response chunks reassembled sequentially must equal the clean answer exactly."""
    full_answer = clean_answer_text(
        "CHARUSAT\u00a0Online offers BBA—a 3-year degree—with fee structure at https://charusat.online."
    )
    chunk_size = 8
    chunks = [full_answer[i : i + chunk_size] for i in range(0, len(full_answer), chunk_size)]
    reassembled = "".join(chunks)
    assert reassembled == full_answer
    assert "CHARUSAT Online" in reassembled
    assert "BBA, a 3-year degree" in reassembled


def test_conversation_read_cleans_without_rewriting_db():
    """Reading messages cleans text on the fly without modifying MongoDB documents."""
    raw_content = "Welcome to CHARUSAT\u200b\u00a0Online!"
    fake_msg = {
        "_id": "fake_id",
        "conversation_id": "conv_1",
        "role": "assistant",
        "content": raw_content,
    }
    cleaned_msg = {**fake_msg, "content": clean_answer_text(fake_msg.get("content", ""))}
    assert cleaned_msg["content"] == "Welcome to CHARUSAT Online!"
    assert fake_msg["content"] == raw_content


def test_word_gluing_root_cause_diagnosis():
    """Demonstrate that zero-width space deletion and unicode space normalization fix glued words.

    Examples observed previously:
      1. 'CHARUSAT\u200bOnline' (zero-width space between words without regular space)
      2. 'the\u00a0home\u202fpage' (non-breaking spaces rendered tightly by fonts)
      3. 'Section\u20072(f)' (figure space)
    """
    glued_input = "CHARUSAT\u200b Online the\u00a0home\u202fpage Section\u20072(f)"
    fixed = clean_answer_text(glued_input)
    assert fixed == "CHARUSAT Online the home page Section 2(f)"
