from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple

from app.conversation import analyze_turn, _detect_programmes_in_text
from app.utils import logger


def extract_key_terms(text: str) -> List[str]:
    """Extract important terms from text for query expansion.
    Handles 3-letter acronyms (e.g. bca, bba, mba, mca).
    """
    stopwords = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "have", "how", "i", "in", "is", "it", "its", "of", "on",
        "or", "that", "the", "this", "to", "was", "what", "when", "where",
        "who", "will", "with", "do", "does", "did", "can", "could", "should",
        "would", "may", "might", "must", "shall",
    }

    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    # Keep words of 3+ letters if not in stopwords (preserves mba, bca, bba, mca, fee)
    key_terms = [w for w in words if w not in stopwords]

    seen = set()
    result = []
    for term in key_terms:
        if term not in seen:
            seen.add(term)
            result.append(term)

    return result


def is_vague_query(query: str) -> bool:
    """Return True if the query is a short, ambiguous or vague question without enough detail."""
    q = query.strip().lower().rstrip("?").strip()
    core = re.sub(
        r"^(?:what(?:'s|\s+is|\s+are)?|how(?:\s+about)?|tell\s+me|can\s+you|please)\s+",
        "",
        q,
    ).strip()
    core = re.sub(r"^(?:the|a|an)\s+", "", core).strip()
    vague_terms = {
        "fees", "fee", "cost", "price", "it", "this", "that",
        "tell me more", "more", "tell me", "details",
        "courses", "course", "program", "programme", "programs", "programmes",
        "duration", "eligibility", "admission", "syllabus", "exam", "exams",
        "subjects", "specialization", "specialisation",
        "fee structure", "fees structure", "fee details", "fees details",
        "eligibility criteria", "admission process", "admission procedure",
        "passing marks", "passing criteria", "minimum passing marks",
        "grading", "grading system", "cgpa", "examination pattern",
        "syllabus details", "course structure", "programme structure",
    }
    return (q in vague_terms or core in vague_terms) or bool(re.match(
        r"^(?:fees?|it|tell\s+me\s+more|more|details?"
        r"|(?:fee|fees|grading)\s+(?:structure|details)"
        r"|passing\s+(?:marks|criteria))\??$",
        core,
    ))


def vague_clarification_message() -> str:
    """Clarification message asking which programme the user wants."""
    return (
        "Which online degree programme are you inquiring about? "
        "CHARUSAT offers Online BCA, Online BBA, Online MBA, and Online MCA programmes. "
        "Please specify which programme you are interested in (e.g. BCA, BBA, MBA, or MCA) "
        "so I can provide the exact details."
    )


def detect_programme_context(history: Optional[List[Any]]) -> Optional[str]:
    """Detect programme context using analyze_turn."""
    if not history:
        return None
    plan = analyze_turn("", history=history)
    return plan.primary_program


def rewrite_pronouns(query: str, history: Optional[List[Any]] = None) -> str:
    """Thin wrapper over analyze_turn."""
    if not history:
        return query
    plan = analyze_turn(query, history=history)
    return plan.standalone_question or query


def expand_query(query: str, history: Optional[List[Any]] = None, max_terms: int = 3) -> str:
    """Thin wrapper over analyze_turn."""
    if not history:
        return query
    plan = analyze_turn(query, history=history)
    return plan.standalone_question or query


def get_contextual_query(
    query: str,
    history: Optional[List[Any]] = None,
    enable_expansion: bool = True,
) -> str:
    """Get a contextualized query for retrieval using analyze_turn."""
    if not history or not enable_expansion:
        return query
    plan = analyze_turn(query, history=history)
    return plan.standalone_question or query

