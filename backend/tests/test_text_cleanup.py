import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.text_cleanup import clean_answer_text


def test_removes_zero_width_without_breaking_words_or_urls():
    value = "CHARUSAT\u200b Online https://example.test/a\u200bpath"
    assert clean_answer_text(value) == "CHARUSAT Online https://example.test/a\u200bpath"


def test_normalizes_spaces_and_table_dash():
    assert clean_answer_text("A\u00a0B\u202fC\u2009D\u200aE\u2007F") == "A B C D E F"
    assert clean_answer_text("| — | value |") == "| N/A | value |"


def test_replaces_em_dash_and_preserves_en_dash():
    assert clean_answer_text("One—two and 2025–26") == "One, two and 2025–26"
