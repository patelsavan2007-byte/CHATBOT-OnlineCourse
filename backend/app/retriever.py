from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

from app.config import TOP_K
from app.utils import logger, print_info


PROGRAM_KEYWORDS: Dict[str, str] = {
    r"\b(?:online\s+)?bca\b": "online_bca",
    r"\b(?:online\s+)?bba\b": "online_bba",
    r"\b(?:online\s+)?mba\b": "online_mba",
    r"\b(?:online\s+)?mca\b": "online_mca",
}

# Attribute keywords used for keyword-based score boosting
ATTRIBUTE_KEYWORDS: Set[str] = {
    "fee", "fees", "annual fee", "total fee", "tuition", "cost", "price",
    "duration", "years", "year",
    "credits", "credit", "total credits",
    "eligibility", "eligible", "criteria", "requirement",
    "admission", "admission process",
    "examination", "exam",
    "syllabus", "curriculum", "semester", "subjects",
    "annual", "total",
}

# How much to boost scores of chunks that match query keywords
KEYWORD_BOOST_FACTOR = 0.25

# Extra boost when a chunk contains a keyword near a concrete value (number/currency)
VALUE_PROXIMITY_BONUS = 0.15


def _detect_program(query: str) -> str:
    query_lower = query.lower()
    for pattern, program_name in PROGRAM_KEYWORDS.items():
        if re.search(pattern, query_lower):
            return program_name
    return ""


def _detect_query_keywords(query: str) -> List[str]:
    """Detect attribute keywords present in the user query."""
    query_lower = query.lower()
    matched = []
    # Check multi-word keywords first, then single-word
    for kw in sorted(ATTRIBUTE_KEYWORDS, key=len, reverse=True):
        if kw in query_lower:
            matched.append(kw)
    return matched


def _has_value_near_keyword(content: str, keywords: List[str]) -> bool:
    """Check if a keyword appears near a concrete value (number, currency, year count)."""
    content_lower = content.lower()
    for kw in keywords:
        # Find all positions of the keyword
        start = 0
        while True:
            idx = content_lower.find(kw, start)
            if idx == -1:
                break
            # Check a window around the keyword for numbers/values
            window_start = max(0, idx - 80)
            window_end = min(len(content_lower), idx + len(kw) + 80)
            window = content_lower[window_start:window_end]
            # Look for numbers, currency symbols, or year patterns
            if re.search(r"[\d₹$]|inr|\d+[,.]?\d*", window):
                return True
            start = idx + 1
    return False


def _boost_results(
    results: List[Tuple[Document, float]],
    query_keywords: List[str],
) -> List[Tuple[Document, float]]:
    """Re-rank results by boosting chunks that contain query keywords."""
    if not query_keywords:
        return results

    boosted: List[Tuple[Document, float]] = []
    for doc, score in results:
        content_lower = doc.page_content.lower()
        # Count how many query keywords appear in this chunk
        matches = sum(1 for kw in query_keywords if kw in content_lower)
        if matches > 0:
            # Base boost proportional to keyword matches
            boost = KEYWORD_BOOST_FACTOR * matches
            # Extra boost if the chunk has a concrete value near the keyword
            if _has_value_near_keyword(doc.page_content, query_keywords):
                boost += VALUE_PROXIMITY_BONUS
                logger.info(
                    "Value-proximity bonus applied to chunk from %s",
                    doc.metadata.get("source", "unknown"),
                )
            new_score = min(score + boost, 1.0)
            logger.info(
                "Boosted chunk (score %.3f -> %.3f, %d keyword matches): %s",
                score, new_score, matches,
                doc.metadata.get("source", "unknown"),
            )
            boosted.append((doc, new_score))
        else:
            boosted.append((doc, score))

    # Re-sort by score descending (higher = more relevant)
    boosted.sort(key=lambda x: x[1], reverse=True)
    return boosted


class RAGRetriever:
    def __init__(self, vector_store: Chroma) -> None:
        self.vector_store = vector_store

    def retrieve(self, query: str) -> List[Tuple[Document, float]]:
        program_name = _detect_program(query)
        filter_args = {"program_name": program_name} if program_name else None
        results: List[Tuple[Document, float]] = []

        if filter_args:
            try:
                results = self.vector_store.similarity_search_with_relevance_scores(query, k=TOP_K, filter=filter_args)
            except Exception as exc:
                logger.warning("Filtered search failed (%s): %s. Trying unfiltered search.", filter_args, exc)
                results = []

            if results:
                print_info(f"Retrieved chunks: {len(results)} (filtered for {program_name})")
                logger.info("Retrieved filtered chunks: %s", len(results))
                for document, score in results:
                    logger.info("Chunk score %.3f from %s", score, document.metadata.get("source", "unknown"))

                query_keywords = _detect_query_keywords(query)
                if query_keywords:
                    results = _boost_results(results, query_keywords)
                    print_info(f"Applied keyword boosting for: {', '.join(query_keywords)}")

                return results

        try:
            results = self.vector_store.similarity_search_with_relevance_scores(query, k=TOP_K)
        except Exception as exc:
            logger.error("Similarity search failed: %s. Falling back to simple similarity search.", exc)
            try:
                docs = self.vector_store.similarity_search(query, k=TOP_K)
                results = [(d, 0.5) for d in docs]
            except Exception as exc2:
                logger.error("Unfiltered search failed: %s", exc2)
                results = []

        print_info(f"Retrieved chunks: {len(results)}")
        logger.info("Retrieved chunks: %s", len(results))
        for document, score in results:
            logger.info("Chunk score %.3f from %s", score, document.metadata.get("source", "unknown"))

        query_keywords = _detect_query_keywords(query)
        if query_keywords:
            results = _boost_results(results, query_keywords)
            print_info(f"Applied keyword boosting for: {', '.join(query_keywords)}")

        return results

