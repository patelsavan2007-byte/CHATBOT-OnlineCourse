from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app import config
from app.deduplicate import apply_diversity_cap, deduplicate_results
from app.source_authority import source_authority_bonus
from app.utils import logger, print_info


PROGRAM_KEYWORDS: Dict[str, str] = {
    r"\b(?:online\s+)?bca\b": "online_bca",
    r"\b(?:online\s+)?bba\b": "online_bba",
    r"\b(?:online\s+)?mba\b": "online_mba",
    r"\b(?:online\s+)?mca\b": "online_mca",
}


def _detect_program(query: str) -> str:
    """Detect the online programme mentioned in the query, if any."""
    query_lower = query.lower()
    for pattern, program_name in PROGRAM_KEYWORDS.items():
        if re.search(pattern, query_lower):
            return program_name
    return ""


def _detect_query_keywords(query: str) -> List[str]:
    """Detect attribute keywords present in the user query.

    Uses the configurable ATTRIBUTE_KEYWORDS set so the vocabulary can be
    extended without touching retrieval code.
    """
    query_lower = query.lower()
    matched = []
    for keyword in sorted(config.ATTRIBUTE_KEYWORDS, key=len, reverse=True):
        if keyword in query_lower:
            matched.append(keyword)
    return matched


def _has_value_near_keyword(content: str, keyword: str) -> bool:
    """Return True if *keyword* appears near a concrete value (number/currency)."""
    content_lower = content.lower()
    start = 0
    while True:
        idx = content_lower.find(keyword, start)
        if idx == -1:
            return False
        window_start = max(0, idx - 80)
        window_end = min(len(content_lower), idx + len(keyword) + 80)
        window = content_lower[window_start:window_end]
        if re.search(r"[\d₹$]|inr", window, re.IGNORECASE):
            return True
        start = idx + 1


def _score_chunk(
    doc: Document,
    base_score: float,
    program_name: str,
    keywords: List[str],
) -> Tuple[float, float, float, float]:
    """Compute the final bounded score for a candidate chunk.

    Semantic relevance remains the primary signal. Keyword matches, value
    proximity and source authority contribute small, individually capped
    bonuses so they can refine ordering without flattening scores onto the
    same maximum. Returns ``(final, keyword_bonus, proximity_bonus, authority_bonus)``.
    """
    content_lower = doc.page_content.lower()
    matched = [kw for kw in keywords if kw in content_lower]

    keyword_bonus = 0.0
    if matched:
        keyword_bonus = min(len(matched) * config.KEYWORD_BOOST_FACTOR, config.KEYWORD_BOOST_MAX)

    proximity_bonus = 0.0
    if matched:
        proximity_hits = sum(1 for kw in matched if _has_value_near_keyword(doc.page_content, kw))
        if proximity_hits:
            proximity_bonus = min(proximity_hits * config.VALUE_PROXIMITY_BONUS, config.VALUE_PROXIMITY_MAX)

    authority_bonus = 0.0
    if config.SOURCE_AUTHORITY_ENABLED:
        authority_bonus = source_authority_bonus(doc.metadata, program_name)

    final = min(
        base_score + keyword_bonus + proximity_bonus + authority_bonus,
        config.SCORE_CAP,
    )
    return final, keyword_bonus, proximity_bonus, authority_bonus


class RAGRetriever:
    """Retrieve, rank, de-duplicate and diversify evidence chunks.

    The pipeline is deliberately general:

    1. a wide candidate pool is fetched from the vector store (programme-scoped
       when a programme is detected);
    2. every candidate receives a small, bounded set of bonuses on top of its
       semantic score (keyword match, value proximity, source authority);
    3. near-duplicates are removed and per-(source, page) diversity is capped;
    4. the final top-K is returned to the answer generator.
    """

    def __init__(self, vector_store: Chroma) -> None:
        self.vector_store = vector_store
        self.last_query: str = ""
        self.last_program: str = ""
        self.last_keywords: List[str] = []
        self.last_pool: List[Tuple[Document, float]] = []
        self._policy_sources_cache: Optional[Set[str]] = None

    # ------------------------------------------------------------------
    # Policy source discovery
    # ------------------------------------------------------------------

    def _policy_sources(self) -> Set[str]:
        """Distinct source filenames that carry general university policy info.

        Website policy pages (terms/privacy/disclosures/admission data) are
        indexed without a ``program_name``. They are discovered once from the
        collection so programme-scoped queries can still find them, and new
        policy files are picked up automatically without hardcoding filenames.
        """
        if self._policy_sources_cache is not None:
            return self._policy_sources_cache

        sources: Set[str] = set()
        try:
            data = self.vector_store.get(where={"program_name": ""}, include=["metadatas"])
        except Exception as exc:
            logger.warning("Policy source discovery failed: %s", exc)
            self._policy_sources_cache = sources
            return sources

        for meta in data.get("metadatas", []) or []:
            source = str(meta.get("source", ""))
            if any(pattern in source for pattern in config.GENERAL_POLICY_SOURCE_PATTERNS):
                sources.add(source)

        self._policy_sources_cache = sources
        if sources:
            logger.info("Discovered %d policy source(s): %s", len(sources), sorted(sources))
        return sources

    # ------------------------------------------------------------------
    # Candidate retrieval
    # ------------------------------------------------------------------

    def _candidate_search(self, query: str, program_name: str) -> List[Tuple[Document, float]]:
        if program_name:
            conditions: List[Dict[str, object]] = [
                {"program_name": program_name},
                {"program_name": "general"},
            ]
            policy_sources = self._policy_sources()
            if policy_sources:
                conditions.append({"source": {"$in": sorted(policy_sources)}})
            filter_args: Dict[str, object] = {"$or": conditions}
            try:
                results = self.vector_store.similarity_search_with_relevance_scores(
                    query, k=config.CANDIDATE_POOL_SIZE, filter=filter_args
                )
                if results:
                    return results
            except Exception as exc:
                logger.warning("Filtered candidate search failed (%s): %s", filter_args, exc)

        try:
            return self.vector_store.similarity_search_with_relevance_scores(
                query, k=config.CANDIDATE_POOL_SIZE
            )
        except Exception as exc:
            logger.error("Similarity search failed: %s", exc)
            try:
                docs = self.vector_store.similarity_search(query, k=config.CANDIDATE_POOL_SIZE)
                return [(doc, 0.5) for doc in docs]
            except Exception as exc2:
                logger.error("Unfiltered search failed: %s", exc2)
                return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(self, query: str) -> List[Tuple[Document, float]]:
        self.last_query = query
        self.last_program = _detect_program(query)
        self.last_keywords = _detect_query_keywords(query)
        program_name = self.last_program

        if program_name:
            print_info(f"Programme detected: {program_name}")
        if self.last_keywords:
            print_info(f"Attribute keywords detected: {', '.join(self.last_keywords)}")

        pool = self._candidate_search(query, program_name)
        if not pool:
            logger.warning("No candidates retrieved for query: %s", query)
            return []

        print_info(f"Retrieved candidate pool: {len(pool)} chunk(s)")

        scored: List[Tuple[Document, float]] = []
        for doc, base_score in pool:
            final, kw, prox, auth = _score_chunk(doc, base_score, program_name, self.last_keywords)
            scored.append((doc, final))
            logger.info(
                "Chunk %s | base %.3f +kw %.3f +prox %.3f +auth %.3f = %.3f",
                doc.metadata.get("source", "unknown"),
                base_score, kw, prox, auth, final,
            )

        scored.sort(key=lambda item: item[1], reverse=True)

        # Filter out low-relevance noise below threshold
        relevant_scored = [item for item in scored if item[1] >= getattr(config, "MIN_RELEVANCE_SCORE", 0.55)]
        if not relevant_scored:
            logger.info("All retrieved candidates fell below minimum relevance score threshold (%.2f)", getattr(config, "MIN_RELEVANCE_SCORE", 0.55))
            self.last_pool = []
            return []

        # Keep the full relevant pool for conflict detection
        self.last_pool = relevant_scored

        kept, _removed_dup = deduplicate_results(relevant_scored)
        kept, _removed_div = apply_diversity_cap(kept)
        final = kept[: config.TOP_K]


        print_info(f"Final selection: {len(final)} chunk(s)")
        for doc, score in final:
            logger.info(
                "Selected %.3f from %s (page %s, %s)",
                score,
                doc.metadata.get("source", "unknown"),
                doc.metadata.get("page", "n/a"),
                doc.metadata.get("content_type", "n/a"),
            )
        return final
