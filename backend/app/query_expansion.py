"""Query expansion and rewrite for multi-turn retrieval.

This module improves retrieval quality by:
1. Expanding queries with relevant terms from conversation history
2. Rewriting pronouns and context-dependent references
3. Maintaining context across multiple conversation turns
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from app.utils import logger


# Pronouns and context-dependent phrases that need rewriting
PRONOUN_PATTERNS = {
    r"\bit\b": "it",
    r"\bthey\b": "they",
    r"\bthem\b": "them",
    r"\bthis\b": "this",
    r"\bthat\b": "that",
    r"\bthese\b": "these",
    r"\bthose\b": "those",
    r"\bthe\s+(?:program|course|degree|one)\b": "the programme",
}


def extract_key_terms(text: str) -> List[str]:
    """Extract important terms from text for query expansion.

    Args:
        text: Input text

    Returns:
        List of key terms
    """
    # Simple keyword extraction based on length and common stopwords
    stopwords = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "have", "how", "i", "in", "is", "it", "its", "of", "on",
        "or", "that", "the", "this", "to", "was", "what", "when", "where",
        "who", "will", "with", "do", "does", "did", "can", "could", "should",
        "would", "may", "might", "must", "shall",
    }

    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    key_terms = [w for w in words if w not in stopwords and len(w) > 3]

    # Remove duplicates while preserving order
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
    return q in {
        "fees", "fee", "cost", "price", "it", "this", "that",
        "tell me more", "more", "tell me", "details",
        "courses", "course", "program", "programme", "programs", "programmes",
        "duration", "eligibility", "admission", "syllabus", "exam", "exams",
        "subjects", "specialization", "specialisation",
    } or bool(re.match(r"^(?:fees?|it|tell\s+me\s+more|more|details?)\??$", q))


def vague_clarification_message() -> str:
    """Clarification message asking which programme the user wants."""
    return (
        "Which online degree programme are you inquiring about? "
        "CHARUSAT offers Online BCA, Online BBA, Online MBA, and Online MCA programmes. "
        "Please specify which programme you are interested in (e.g. BCA, BBA, MBA, or MCA) "
        "so I can provide the exact details."
    )


def detect_programme_context(history: List[Tuple[str, str]]) -> Optional[str]:
    """Detect the programme being discussed from conversation history.

    Checks user messages and assistant responses in the most recent turns.
    """
    programme_patterns = [
        (re.compile(r"\b(?:online\s+)?b\.?\s*c\.?\s*a\b", re.IGNORECASE), "online_bca"),
        (re.compile(r"\b(?:online\s+)?b\.?\s*b\.?\s*a\b", re.IGNORECASE), "online_bba"),
        (re.compile(r"\b(?:online\s+)?m\.?\s*b\.?\s*a\b", re.IGNORECASE), "online_mba"),
        (re.compile(r"\b(?:online\s+)?m\.?\s*c\.?\s*a\b", re.IGNORECASE), "online_mca"),
    ]

    for user_msg, asst_msg in reversed(history[-5:]):
        combined = f"{user_msg} {asst_msg}"
        for pattern, programme in programme_patterns:
            if pattern.search(combined):
                logger.info("Detected programme context from history: %s", programme)
                return programme

    return None


def rewrite_pronouns(query: str, history: List[Tuple[str, str]]) -> str:
    """Rewrite pronouns and context-dependent references in the query.

    Args:
        query: Current user query
        history: Conversation history

    Returns:
        Rewritten query with pronouns resolved
    """
    if not history:
        return query

    programme = detect_programme_context(history)
    if programme:
        programme_display = programme.replace("_", " ").upper()
        q_clean = query.strip().lower().rstrip("?").strip()

        # Handle purely vague follow-ups using known programme
        if q_clean in {"fees", "fee", "cost"}:
            return f"What is the fee structure for {programme_display}?"
        if q_clean in {"tell me more", "more", "details"}:
            return f"Tell me more about the {programme_display} programme."
        if q_clean in {"it", "this", "that"}:
            return f"Tell me about the {programme_display} programme."

        # Pronoun substitution
        rewritten = re.sub(r"\b(?:it|this|that|the programme|the course)\b", programme_display, query, flags=re.IGNORECASE)
        if rewritten != query:
            logger.info("Rewrote pronouns with programme: %s -> %s", query, rewritten)
            return rewritten

        # If query has attribute keywords but no programme, append programme
        if not any(prog in query.lower() for prog in ["bba", "bca", "mba", "mca"]):
            if any(term in query.lower() for term in ["fee", "cost", "duration", "semester", "credit", "eligib", "admiss", "curric", "exam"]):
                rewritten = f"{query} for {programme_display}"
                logger.info("Rewrote query with programme context: %s -> %s", query, rewritten)
                return rewritten

    return query


def expand_query(
    query: str,
    history: Optional[List[Tuple[str, str]]] = None,
    max_terms: int = 3,
) -> str:
    """Expand query using key terms from the PREVIOUS TURN ONLY.

    Args:
        query: Current user query
        history: Conversation history (list of (user, assistant) tuples)
        max_terms: Maximum number of expansion terms to add (default 3)

    Returns:
        Expanded query
    """
    if not history:
        return query

    # First rewrite pronouns and vague references
    rewritten = rewrite_pronouns(query, history)

    # Extract key terms from PREVIOUS TURN ONLY (history[-1])
    all_terms = []
    prev_turn = history[-1]
    # Extract terms from previous user message
    all_terms.extend(extract_key_terms(prev_turn[0]))

    # Extract terms from current query
    current_terms = extract_key_terms(query)

    # Find expansion terms not already in current query
    expansion_terms = [t for t in all_terms if t not in current_terms]
    expansion_terms = list(dict.fromkeys(expansion_terms))[:max_terms]

    if expansion_terms:
        expanded = f"{rewritten} {' '.join(expansion_terms)}"
        logger.info("Expanded query: %s -> %s (added terms: %s)", query, expanded, expansion_terms)
        return expanded

    return rewritten


def get_contextual_query(
    query: str,
    history: Optional[List[Tuple[str, str]]] = None,
    enable_expansion: bool = True,
) -> str:
    """Get a contextualized query for retrieval.

    This combines query rewriting and expansion to improve retrieval
    quality in multi-turn conversations.

    Args:
        query: Current user query
        history: Conversation history
        enable_expansion: Whether to enable query expansion

    Returns:
        Contextualized query
    """
    if not history or not enable_expansion:
        return query

    # Apply expansion
    contextual_query = expand_query(query, history)

    return contextual_query
