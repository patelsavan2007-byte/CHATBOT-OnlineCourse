from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app import config
from app.deduplicate import apply_diversity_cap, deduplicate_results
from app.source_authority import source_authority_bonus
from app.utils import logger


# Intent tags describing how a query should be routed through retrieval.
INTENT_PROGRAMME = "programme"            # a specific programme is mentioned
INTENT_OVERVIEW = "programme_overview"    # asks what programmes are offered
INTENT_GENERAL = "general"                # generic university-level question


PROGRAM_KEYWORDS: Dict[str, str] = {
    r"\b(?:online\s+)?b\.?\s*c\.?\s*a\b": "online_bca",
    r"\b(?:online\s+)?b\.?\s*b\.?\s*a\b": "online_bba",
    r"\b(?:online\s+)?m\.?\s*b\.?\s*a\b": "online_mba",
    r"\b(?:online\s+)?m\.?\s*c\.?\s*a\b": "online_mca",
}


def _detect_program(query: str) -> str:
    """Detect the online programme explicitly mentioned in the query, if any.

    A programme is only assigned when the user actually names one
    (BCA/BBA/MBA/MCA, with or without dots, "online" prefix or
    whitespace). Generic queries never inherit a default programme.
    """
    query_lower = query.lower()
    for pattern, program_name in PROGRAM_KEYWORDS.items():
        if re.search(pattern, query_lower):
            return program_name
    return ""


def _analyze_query(query: str) -> Tuple[str, str]:
    """Classify a query into ``(program, intent)``.

    Programme-specific queries keep the detected programme and the
    ``programme`` intent. Questions asking what is offered are routed to the
    overview intent. Everything else is treated as a generic question that
    must be answered from a balanced set of documents rather than a single
    default programme.
    """
    program = _detect_program(query)
    if program:
        return program, INTENT_PROGRAMME
    if _is_programme_overview_query(query):
        return "", INTENT_OVERVIEW
    return "", INTENT_GENERAL


def _is_programme_overview_query(query: str) -> bool:
    """Detect broad queries asking what programmes/courses are offered or available."""
    patterns = [
        r"\b(?:what|which|list|available|all)\b.*\b(?:program|programme|course|degree)s?\b",
        r"\b(?:program|programme|course|degree)s?\b.*\b(?:offer|offered|available|provide|provided)\b",
    ]
    return any(re.search(p, query, re.IGNORECASE) for p in patterns)


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


_STOPWORDS = frozenset(
    "a an and are as at be by for from has have how i in is it its of on or "
    "that the this to was were will with do does did what which when where why "
    "would could should can may might about than into over under"
    .split()
)


def _query_phrases(query: str) -> List[str]:
    """Extract meaningful 2-3 word phrases from the query.

    Weak filler phrases ("what is the ...", "is the ...") are discarded so a
    common 2-gram cannot match every chunk. Kept phrases must be dominated by
    content words: 3-grams need at least two, 2-grams need both. Verbatim
    phrase overlap between the question and a chunk is a strong,
    document-independent relevance signal that rescues the correct chunk when
    the embedding ranker favours loosely-related boilerplate.
    """
    words = re.findall(r"[a-z0-9']+", query.lower())
    phrases: List[str] = []
    for size in (3, 2):
        for i in range(len(words) - size + 1):
            candidate = words[i:i + size]
            significant = sum(1 for w in candidate if w not in _STOPWORDS)
            required = 2 if size == 3 else 2
            if significant >= required:
                phrases.append(" ".join(candidate))
    return phrases


def _score_chunk(
    doc: Document,
    base_score: float,
    program_name: str,
    keywords: List[str],
    phrases: Optional[List[str]] = None,
) -> Tuple[float, float, float, float, float]:
    """Compute the final bounded score for a candidate chunk.

    Semantic relevance remains the primary signal. Keyword matches, value
    proximity, verbatim phrase overlap and source authority contribute small,
    individually capped bonuses so they can refine ordering without
    flattening scores onto the same maximum. Returns
    ``(final, keyword_bonus, proximity_bonus, phrase_bonus, authority_bonus)``.
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

    phrase_bonus = 0.0
    phrase_matched = bool(phrases) and any(phrase in content_lower for phrase in phrases)
    if phrase_matched:
        phrase_bonus = config.PHRASE_MATCH_BONUS

    authority_bonus = 0.0
    if config.SOURCE_AUTHORITY_ENABLED:
        authority_bonus = source_authority_bonus(doc.metadata, program_name)

    final = min(
        base_score + keyword_bonus + proximity_bonus + phrase_bonus + authority_bonus,
        config.SCORE_CAP,
    )

    # A chunk containing the user's exact multi-word phrase is definitionally
    # on-topic. The embedding ranker can still score it low (legal boilerplate
    # routinely outscores the correct chunk), so phrase-matched chunks are
    # guaranteed to clear the relevance floor instead of being dropped as
    # noise. Without this, genuinely-correct answers such as "Placement
    # Assistance" in home.md or "technical support" in ciqa.md would never be
    # retrieved.
    if phrase_matched and final < config.MIN_RELEVANCE_SCORE:
        final = config.MIN_RELEVANCE_SCORE

    return final, keyword_bonus, proximity_bonus, phrase_bonus, authority_bonus


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
        self.last_intent: str = INTENT_GENERAL
        self.last_keywords: List[str] = []
        self.last_phrases: List[str] = []
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
        """Route candidate retrieval by query intent.

        * ``programme``        -> the detected programme plus general policy docs
        * ``programme_overview`` -> one sample per offered programme
        * ``general``          -> a balanced pool across all programmes and the
                                   general/policy documents (never a single
                                   default programme)

        Generic and overview searches are augmented with verbatim-phrase
        candidates so a small, topically-correct chunk buried below the
        embedding ranking can still be retrieved.
        """
        intent = self.last_intent
        if intent == INTENT_PROGRAMME:
            return self._programme_candidate_search(query, program_name)
        if intent == INTENT_OVERVIEW:
            pool = self._overview_candidate_search(query)
        else:
            pool = self._general_candidate_search(query)
        return self._merge_phrase_candidates(pool)

    def _phrase_candidates(self) -> List[Tuple[Document, float]]:
        """Return chunks containing one of the meaningful query phrases verbatim.

        Semantic retrieval can bury a small, topically-correct chunk (for
        example the "Placement Assistance" bullet on the homepage) far below
        the candidate depth of its group. Chroma's substring search over the
        stored documents guarantees that any chunk containing an exact
        multi-word query phrase is considered. Such chunks have no meaningful
        semantic score, so they enter at the relevance floor and the shared
        scorer places them above unrelated content.
        """
        collection = getattr(self.vector_store, "_collection", None)
        if collection is None or not self.last_phrases:
            return []
        hits: List[Tuple[Document, float]] = []
        seen_ids: Set[str] = set()
        for phrase in self.last_phrases:
            pattern = "(?i)" + re.escape(phrase)
            try:
                got = collection.get(where_document={"$regex": pattern}, include=["metadatas"])
            except Exception as exc:
                logger.warning("Phrase regex search failed for %r: %s", phrase, exc)
                continue
            for cid in got.get("ids") or []:
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                try:
                    docs = self.vector_store.get_by_ids([cid])
                except Exception:
                    continue
                if docs and getattr(docs[0], "page_content", "").strip():
                    hits.append((docs[0], config.MIN_RELEVANCE_SCORE))
        return hits

    def _merge_phrase_candidates(
        self, pool: List[Tuple[Document, float]],
    ) -> List[Tuple[Document, float]]:
        """Merge verbatim-phrase candidates into the pool (deduped by content)."""
        if not self.last_phrases:
            return pool
        seen = {doc.page_content.strip()[:100] for doc, _ in pool}
        merged = list(pool)
        for doc, score in self._phrase_candidates():
            if doc.page_content.strip()[:100] in seen:
                continue
            seen.add(doc.page_content.strip()[:100])
            merged.append((doc, score))
        return merged

    def _programme_candidate_search(
        self, query: str, program_name: str,
    ) -> List[Tuple[Document, float]]:
        """Search scoped to the detected programme plus general policy docs."""
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

    def _overview_candidate_search(self, query: str) -> List[Tuple[Document, float]]:
        """Query each offered programme and merge with the general pool."""
        try:
            all_progs = ["online_bca", "online_bba", "online_mba", "online_mca"]
            prog_candidates: List[Tuple[Document, float]] = []
            for p in all_progs:
                try:
                    p_res = self.vector_store.similarity_search_with_relevance_scores(
                        query, k=5, filter={"program_name": p}
                    )
                    prog_candidates.extend(p_res)
                except Exception:
                    pass
            gen_results = self.vector_store.similarity_search_with_relevance_scores(
                query, k=config.CANDIDATE_POOL_SIZE
            )
            seen: Dict[str, Tuple[Document, float]] = {}
            for doc, score in (prog_candidates + gen_results):
                doc_id = doc.page_content.strip()[:100]
                if doc_id not in seen or score > seen[doc_id][1]:
                    seen[doc_id] = (doc, score)
            combined = list(seen.values())
            combined.sort(key=lambda item: item[1], reverse=True)
            return combined
        except Exception as exc:
            logger.warning("Programme overview query search failed: %s", exc)
            try:
                return self.vector_store.similarity_search_with_relevance_scores(
                    query, k=config.CANDIDATE_POOL_SIZE
                )
            except Exception as exc2:
                logger.error("Overview fallback search failed: %s", exc2)
                return []

    def _general_candidate_search(self, query: str) -> List[Tuple[Document, float]]:
        """Balanced candidate pool for generic university-level questions.

        Each source group (every programme, the general policy documents and
        the generic website pages) is queried separately with a modest per-group
        depth. Without this grouping, a generic question such as "Is the online
        degree UGC-recognised?" would collapse onto the chunks of a single
        programme whose page happens to repeat general university information.
        """
        seen: Dict[str, Tuple[Document, float]] = {}
        groups = [
            "online_bca", "online_bba", "online_mba", "online_mca",
            "general", "",
        ]
        for group in groups:
            try:
                results = self.vector_store.similarity_search_with_relevance_scores(
                    query,
                    k=config.GENERIC_POOL_PER_GROUP,
                    filter={"program_name": group},
                )
            except Exception as exc:
                logger.warning("Group search failed for %r: %s", group, exc)
                continue
            for doc, score in results:
                doc_id = doc.page_content.strip()[:100]
                if doc_id not in seen or score > seen[doc_id][1]:
                    seen[doc_id] = (doc, score)

        combined = list(seen.values())
        combined.sort(key=lambda item: item[1], reverse=True)
        return combined

    def _overview_boost_and_diversify(
        self, scored: List[Tuple[Document, float]],
    ) -> List[Tuple[Document, float]]:
        """Boost official programme overview pages and spread across programmes."""
        boosted = []
        for doc, score in scored:
            src = str(doc.metadata.get("source", ""))
            if src.startswith("programs/online_"):
                score = min(score + 0.10, config.SCORE_CAP)
            boosted.append((doc, score))
        boosted.sort(key=lambda item: item[1], reverse=True)

        from collections import defaultdict
        prog_counts: defaultdict[str, int] = defaultdict(int)
        diversified = []
        for doc, score in boosted:
            pname = str(doc.metadata.get("program_name", ""))
            if not pname:
                continue
            if prog_counts[pname] >= 1:
                continue
            prog_counts[pname] += 1
            diversified.append((doc, score))

        if len(diversified) < config.TOP_K:
            seen_ids = {d.page_content.strip()[:100] for d, _ in diversified}
            for doc, score in boosted:
                if doc.page_content.strip()[:100] not in seen_ids:
                    diversified.append((doc, score))
                    if len(diversified) >= config.TOP_K:
                        break
        return diversified

    @staticmethod
    def _general_diversify(
        scored: List[Tuple[Document, float]],
    ) -> List[Tuple[Document, float]]:
        """Cap how many chunks a single programme may contribute to generic answers."""
        from collections import defaultdict
        counts: defaultdict[str, int] = defaultdict(int)
        result = []
        for doc, score in scored:
            pname = str(doc.metadata.get("program_name", "") or "")
            if pname and counts[pname] >= config.GENERIC_MAX_PER_PROGRAMME:
                continue
            if pname:
                counts[pname] += 1
            result.append((doc, score))
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(self, query: str) -> List[Tuple[Document, float]]:
        self.last_query = query
        self.last_program, self.last_intent = _analyze_query(query)
        self.last_keywords = _detect_query_keywords(query)
        self.last_phrases = _query_phrases(query)
        program_name = self.last_program

        pool = self._candidate_search(query, program_name)
        if not pool:
            logger.warning("No candidates retrieved for query: %s", query)
            return []

        scored: List[Tuple[Document, float]] = []
        for doc, base_score in pool:
            final, *_ = _score_chunk(
                doc, base_score, program_name, self.last_keywords, self.last_phrases,
            )
            scored.append((doc, final))

        scored.sort(key=lambda item: item[1], reverse=True)

        if self.last_intent == INTENT_OVERVIEW:
            scored = self._overview_boost_and_diversify(scored)
        elif self.last_intent == INTENT_GENERAL:
            scored = self._general_diversify(scored)

        # Filter out low-relevance noise below threshold
        relevant_scored = [item for item in scored if item[1] >= getattr(config, "MIN_RELEVANCE_SCORE", 0.52)]
        if not relevant_scored:
            logger.info("All retrieved candidates fell below minimum relevance score threshold (%.2f)", getattr(config, "MIN_RELEVANCE_SCORE", 0.55))
            self.last_pool = []
            return []

        # Keep the full relevant pool for conflict detection
        self.last_pool = relevant_scored

        kept, _removed_dup = deduplicate_results(relevant_scored)
        kept, _removed_div = apply_diversity_cap(kept)
        final = kept[: config.TOP_K]

        return final
