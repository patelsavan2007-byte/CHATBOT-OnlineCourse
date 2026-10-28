from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app import config
from app.deduplicate import apply_diversity_cap, deduplicate_results
from app.source_authority import source_authority_bonus
from app.utils import logger

try:
    from app.hybrid_retrieval import HybridRetriever
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False
    logger.warning("Hybrid retrieval not available (rank-bm25 not installed)")

try:
    from app.reranker import create_reranker
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    logger.warning("Reranker not available (FlagEmbedding or cohere not installed)")

try:
    from app.query_expansion import get_contextual_query
    QUERY_EXPANSION_AVAILABLE = True
except ImportError:
    QUERY_EXPANSION_AVAILABLE = False
    logger.warning("Query expansion not available")


from app.conversation import TurnPlan, analyze_turn, _detect_programmes_in_text

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

    Returns the programme identifier if exactly one programme is mentioned.
    If multiple programmes are named (e.g. comparison or broad question),
    returns empty string so the search is routed across programmes rather
    than locking onto the first dict key.
    """
    progs = _detect_programmes_in_text(query)
    if len(progs) == 1:
        return progs[0]
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


ALL_PROGRAM_NAMES: List[str] = ["online_bca", "online_bba", "online_mba", "online_mca"]

# Attribute words that vary per programme. When one of these is asked WITH
# no programme named, the answer must cover every programme (e.g. "How many
# semesters are there?" -> semester count for BBA, BCA, MBA and MCA).
_CROSS_PROGRAM_ATTR_RE = re.compile(
    r"\b(?:semesters?|duration|how\s+long|how\s+many\s+semesters?|"
    r"fees?|tuition|credits?|curriculum|syllabus|subjects?|"
    r"specialisations?|specializations?)\b",
    re.IGNORECASE,
)


def _requires_all_program_coverage(query: str) -> bool:
    """True for generic attribute questions where every programme's value
    should be reported (short semester counts, durations, fees, credits)."""
    return bool(_CROSS_PROGRAM_ATTR_RE.search(query))


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

    # Add ordinal/cardinal equivalents for year references so table headers match
    q_lower = query.lower()
    year_map = {
        "1": ["1st year", "first year", "year 1"],
        "2": ["2nd year", "second year", "year 2"],
        "3": ["3rd year", "third year", "year 3"],
    }
    for yr, forms in year_map.items():
        if any(f in q_lower for f in forms):
            for f in forms:
                if f not in phrases:
                    phrases.append(f)
            if "fee" in q_lower:
                fee_phrase = f"fee for {forms[0]}"
                if fee_phrase not in phrases:
                    phrases.append(fee_phrase)

    # Filter out phrases consisting solely of programme keywords and stop words
    prog_stopwords = {
        "online", "bba", "bca", "mba", "mca", "program", "programme",
        "programmes", "courses", "course", "degree", "university",
    }
    filtered_phrases = []
    for p in phrases:
        tokens = p.split()
        if any(tok not in prog_stopwords and tok not in _STOPWORDS for tok in tokens):
            filtered_phrases.append(p)

    return filtered_phrases


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

    return final, keyword_bonus, proximity_bonus, phrase_bonus, authority_bonus


class RAGRetriever:
    """Retrieve, rank, de-duplicate and diversify evidence chunks.

    The pipeline is deliberately general:

    1. a wide candidate pool is fetched from the vector store (programme-scoped
       when a programme is detected) using hybrid retrieval (semantic + BM25);
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
        self._hybrid_retriever: Optional[HybridRetriever] = None
        self._reranker = None

        # Initialize hybrid retriever if available
        if HYBRID_AVAILABLE:
            try:
                # Load all documents for BM25 indexing
                all_docs = []
                try:
                    data = self.vector_store.get(include=["documents", "metadatas"])
                    for doc_text, meta in zip(data.get("documents", []), data.get("metadatas", [])):
                        if doc_text and doc_text.strip():
                            all_docs.append(Document(page_content=doc_text, metadata=meta))
                except Exception as exc:
                    logger.warning("Failed to load documents for hybrid retrieval: %s", exc)

                if all_docs:
                    self._hybrid_retriever = HybridRetriever(vector_store, all_docs)
                    logger.info("Hybrid retrieval initialized with %d documents", len(all_docs))
            except Exception as exc:
                logger.warning("Failed to initialize hybrid retriever: %s", exc)

        # Initialize reranker if available and enabled
        if RERANKER_AVAILABLE and config.RERANKER_ENABLED:
            try:
                self._reranker = create_reranker(
                    reranker_type=config.RERANKER_TYPE,
                    model_name=config.RERANKER_MODEL,
                )
                logger.info("Reranker initialized: %s (%s)", config.RERANKER_TYPE, config.RERANKER_MODEL)
            except Exception as exc:
                logger.warning("Failed to initialize reranker: %s", exc)

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

    def _candidate_search(
        self,
        query: str,
        program_name: str,
        intent: Optional[str] = None,
        phrases: Optional[List[str]] = None,
    ) -> List[Tuple[Document, float]]:
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
        if intent is None:
            intent = self.last_intent
        if intent == INTENT_PROGRAMME:
            return self._programme_candidate_search(query, program_name)
        if intent == INTENT_OVERVIEW:
            pool = self._overview_candidate_search(query)
        else:
            pool = self._general_candidate_search(query)
        return self._merge_phrase_candidates(pool, phrases=phrases)

    def _phrase_candidates(self, phrases: Optional[List[str]] = None) -> List[Tuple[Document, float]]:
        """Return chunks containing one of the meaningful query phrases verbatim.

        Semantic retrieval can bury a small, topically-correct chunk (for
        example the "Placement Assistance" bullet on the homepage) far below
        the candidate depth of its group. Chroma's substring search over the
        stored documents guarantees that any chunk containing an exact
        multi-word query phrase is considered. Such chunks have no meaningful
        semantic score, so they enter at the relevance floor and the shared
        scorer places them above unrelated content.
        """
        target_phrases = phrases if phrases is not None else self.last_phrases
        collection = getattr(self.vector_store, "_collection", None)
        if collection is None or not target_phrases:
            return []
        hits: List[Tuple[Document, float]] = []
        seen_ids: Set[str] = set()
        for phrase in target_phrases:
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
        self, pool: List[Tuple[Document, float]], phrases: Optional[List[str]] = None,
    ) -> List[Tuple[Document, float]]:
        """Merge verbatim-phrase candidates into the pool (deduped by content)."""
        target_phrases = phrases if phrases is not None else self.last_phrases
        if not target_phrases:
            return pool
        seen = {doc.page_content.strip()[:100] for doc, _ in pool}
        merged = list(pool)
        for doc, score in self._phrase_candidates(phrases=target_phrases):
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

        # Use hybrid retrieval if available
        if self._hybrid_retriever:
            try:
                results = self._hybrid_retriever.hybrid_search(
                    query, k=config.CANDIDATE_POOL_SIZE, filter=filter_args
                )
                if results:
                    return results
            except Exception as exc:
                logger.warning("Hybrid search failed (%s): %s", filter_args, exc)

        # Fallback to semantic search
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

    def _fee_candidate_search(self, program_name: str) -> List[Tuple[Document, float]]:
        """Retrieve fee structure chunks specifically for a given programme."""
        query = f"fee structure semester tuition examination fee {program_name}"
        return self._programme_candidate_search(query, program_name)[:2]

    def _overview_candidate_search(self, query: str) -> List[Tuple[Document, float]]:
        """Query each offered programme and merge with the general pool."""
        try:
            all_progs = ["online_bca", "online_bba", "online_mba", "online_mca"]
            prog_candidates: List[Tuple[Document, float]] = []
            for p in all_progs:
                try:
                    # Use hybrid retrieval if available
                    if self._hybrid_retriever:
                        p_res = self._hybrid_retriever.hybrid_search(
                            query, k=5, filter={"program_name": p}
                        )
                    else:
                        p_res = self.vector_store.similarity_search_with_relevance_scores(
                            query, k=5, filter={"program_name": p}
                        )
                    prog_candidates.extend(p_res)
                except Exception:
                    pass

            # Use hybrid retrieval for general pool if available
            if self._hybrid_retriever:
                gen_results = self._hybrid_retriever.hybrid_search(
                    query, k=config.CANDIDATE_POOL_SIZE
                )
            else:
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
                # Use hybrid retrieval if available
                if self._hybrid_retriever:
                    results = self._hybrid_retriever.hybrid_search(
                        query,
                        k=config.GENERIC_POOL_PER_GROUP,
                        filter={"program_name": group},
                    )
                else:
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

    def _curriculum_candidate_search(
        self,
        prog: str,
        year: Optional[int] = None,
        semester: Optional[int] = None,
    ) -> List[Tuple[Document, float]]:
        """Retrieve semester chunks of the programme from markdown and PDF."""
        target_sems: List[str] = []
        if semester is not None:
            roman = {1: "i", 2: "ii", 3: "iii", 4: "iv", 5: "v", 6: "vi"}.get(semester, str(semester))
            target_sems = [f"semester {semester}", f"semester {roman}", f"sem-{roman}", f"sem {semester}"]
        elif year is not None:
            sems = {1: [1, 2], 2: [3, 4], 3: [5, 6]}.get(year, [])
            for s in sems:
                roman = {1: "i", 2: "ii", 3: "iii", 4: "iv", 5: "v", 6: "vi"}.get(s, str(s))
                target_sems.extend([f"semester {s}", f"semester {roman}", f"sem-{roman}", f"sem {s}"])
            if year == 2:
                target_sems.extend(["specialization courses", "sem-iii & iv"])
            elif year == 3:
                target_sems.extend(["specialization courses", "sem-v"])
        else:
            target_sems = [
                "semester i", "semester ii", "semester iii", "semester iv",
                "semester v", "semester vi", "semester 1", "semester 2",
                "semester 3", "semester 4", "semester 5", "semester 6",
                "curriculum & syllabus", "specialization courses",
            ]

        results: List[Tuple[Document, float]] = []
        seen = set()

        collection = getattr(self.vector_store, "_collection", None)
        if collection is None:
            return []

        try:
            data = collection.get(
                where={"program_name": prog},
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            logger.warning("Curriculum search failed for %s: %s", prog, exc)
            return []

        for doc_text, meta in zip(data.get("documents", []), data.get("metadatas", [])):
            if not doc_text or not doc_text.strip():
                continue
            doc_lower = doc_text.lower()
            if any(t in doc_lower for t in target_sems):
                if "testimonial" in doc_lower and "semester" not in doc_lower[:80]:
                    continue
                cid = meta.get("chunk_id")
                key = (str(meta.get("source", "")), meta.get("page"), cid)
                if key not in seen:
                    seen.add(key)
                    results.append((Document(page_content=doc_text, metadata=meta), 0.88))

        return results

    def _specialization_candidate_search(
        self, prog: str,
    ) -> List[Tuple[Document, float]]:
        """Retrieve specialization table and course chunks for the programme."""
        collection = getattr(self.vector_store, "_collection", None)
        if collection is None:
            return []

        try:
            data = collection.get(
                where={"program_name": prog},
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            logger.warning("Specialization search failed for %s: %s", prog, exc)
            return []

        results: List[Tuple[Document, float]] = []
        seen = set()

        for doc_text, meta in zip(data.get("documents", []), data.get("metadatas", [])):
            if not doc_text or not doc_text.strip():
                continue
            doc_lower = doc_text.lower()
            if any(t in doc_lower for t in ("specialization", "specialisation", "elective")):
                if "testimonial" in doc_lower:
                    continue
                cid = meta.get("chunk_id")
                key = (str(meta.get("source", "")), meta.get("page"), cid)
                if key not in seen:
                    seen.add(key)
                    results.append((Document(page_content=doc_text, metadata=meta), 0.88))

        return results

    def _fee_candidate_search(
        self, prog: str,
    ) -> List[Tuple[Document, float]]:
        """Retrieve fee structure chunks for the programme."""
        collection = getattr(self.vector_store, "_collection", None)
        if collection is None:
            return []

        try:
            data = collection.get(
                where={"program_name": prog},
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            logger.warning("Fee search failed for %s: %s", prog, exc)
            return []

        results: List[Tuple[Document, float]] = []
        seen = set()

        for doc_text, meta in zip(data.get("documents", []), data.get("metadatas", [])):
            if not doc_text or not doc_text.strip():
                continue
            doc_lower = doc_text.lower()
            if ("fee" in doc_lower or "fees" in doc_lower or "tuition" in doc_lower) and any(
                term in doc_lower for term in ("annual fee", "programme fee", "fee structure", "examination fee", "per year", "total fee", "cost estimate", "programme fee structure", "1500 inr", "fee for 1st year")
            ):
                if "testimonial" in doc_lower:
                    continue
                cid = meta.get("chunk_id")
                key = (str(meta.get("source", "")), meta.get("page"), cid)
                if key not in seen:
                    seen.add(key)
                    results.append((Document(page_content=doc_text, metadata=meta), 0.88))

        return results

    def _faculty_candidate_search(
        self, prog: str = "",
    ) -> List[Tuple[Document, float]]:
        """Retrieve faculty roster and teaching staff chunks."""
        collection = getattr(self.vector_store, "_collection", None)
        if collection is None:
            return []

        try:
            data = collection.get(include=["documents", "metadatas"])
        except Exception as exc:
            logger.warning("Faculty search failed: %s", exc)
            return []

        results: List[Tuple[Document, float]] = []
        seen = set()
        prog_lower = (prog or "").lower()

        prominent_faculty = (
            "dr. dharmendra patel", "dr. atul patel", "dr. binit patel",
            "dr. reshma sable", "dr. sanskruti patel", "dr. jaimin undavia",
            "dr. rajesh sadhwani", "dr. bhaskar pandya", "dr. gaurav rajput",
        )

        for doc_text, meta in zip(data.get("documents", []), data.get("metadatas", [])):
            if not doc_text or not doc_text.strip():
                continue
            doc_lower = doc_text.lower()
            src = str(meta.get("source", "")).lower()

            if "testimonial" in doc_lower:
                continue

            is_match = False
            if "our faculty" in doc_lower or "faculty for b" in doc_lower or "faculty for m" in doc_lower or "faculty of computer" in doc_lower:
                is_match = True
            elif any(prof in doc_lower for prof in prominent_faculty):
                is_match = True

            if is_match:
                score = 0.92
                if "home.md" in src and ("faculty for bba" in doc_lower or "faculty for bca" in doc_lower):
                    score = 0.98
                p_name = str(meta.get("program_name", "")).lower()
                if prog_lower and p_name:
                    if prog_lower in p_name:
                        score = 0.96
                    else:
                        score = 0.86
                cid = meta.get("chunk_id")
                key = (src, meta.get("page"), cid, doc_text[:50])
                if key not in seen:
                    seen.add(key)
                    results.append((Document(page_content=doc_text, metadata=meta), score))

        results.sort(key=lambda item: item[1], reverse=True)
        return results

    def _contact_candidate_search(self) -> List[Tuple[Document, float]]:
        """Retrieve official contact directory chunks."""
        collection = getattr(self.vector_store, "_collection", None)
        if collection is None:
            return []
        try:
            data = collection.get(
                where={"source": "contact_directory.md"},
                include=["documents", "metadatas"],
            )
        except Exception:
            try:
                data = collection.get(include=["documents", "metadatas"])
            except Exception as exc:
                logger.warning("Contact search failed: %s", exc)
                return []

        results: List[Tuple[Document, float]] = []
        seen = set()
        for doc_text, meta in zip(data.get("documents", []), data.get("metadatas", [])):
            if not doc_text or not doc_text.strip():
                continue
            src = str(meta.get("source", "")).lower()
            if "contact.md" in src or "contact details" in doc_text.lower():
                key = (src, meta.get("chunk_id"))
                if key not in seen:
                    seen.add(key)
                    results.append((Document(page_content=doc_text, metadata=meta), 0.96))
        return results

    def _compare_candidate_search(
        self, query: str, plan: TurnPlan,
    ) -> List[Tuple[Document, float]]:
        """A separate sub-retrieval per programme, merged."""
        from app.lexicon import is_topic_programme_independent
        is_indep = is_topic_programme_independent(plan.topic) if (plan and plan.topic) else False
        explicit_progs = _detect_programmes_in_text(query) if query else (
            _detect_programmes_in_text(plan.raw_question) if (plan and plan.raw_question) else []
        )
        target_progs = explicit_progs if explicit_progs else (
            plan.programmes if (plan and plan.programmes and not is_indep) else ALL_PROGRAM_NAMES
        )
        merged_results: List[Tuple[Document, float]] = []
        seen = set()

        for prog in target_progs:
            prog_label = prog.replace("online_", "").upper()
            if plan.topic == "fees":
                sub_query = f"fee structure fees for {prog_label}"
            elif plan.topic:
                sub_query = f"{plan.topic} for {prog_label}"
            else:
                sub_query = f"{query} {prog_label}"

            prog_pool = self._programme_candidate_search(sub_query, prog)
            if plan.topic == "subjects":
                curr_chunks = self._curriculum_candidate_search(prog, plan.year, plan.semester)
                prog_pool = list(curr_chunks) + list(prog_pool)
            elif plan.topic == "specializations":
                spec_chunks = self._specialization_candidate_search(prog)
                prog_pool = list(spec_chunks) + list(prog_pool)
            elif plan.topic == "fees":
                fee_chunks = self._fee_candidate_search(prog)
                prog_pool = list(fee_chunks) + list(prog_pool)

            for doc, base_score in prog_pool:
                content_key = doc.page_content.strip()[:100]
                if content_key not in seen:
                    merged_results.append((doc, base_score))
                    seen.add(content_key)

        # Include general candidate search results for policy/university-level info
        gen_pool = self._general_candidate_search(query)
        for doc, score in gen_pool:
            pname = str(doc.metadata.get("program_name", "") or "")
            if pname not in ("", "general"):
                continue
            content_key = doc.page_content.strip()[:100]
            if content_key not in seen:
                seen.add(content_key)
                merged_results.append((doc, score))

        return self._merge_phrase_candidates(merged_results)


    def _ensure_multi_program_coverage(
        self,
        pool: List[Tuple[Document, float]],
        target_progs: List[str],
        min_per_prog: int = 2,
    ) -> List[Tuple[Document, float]]:
        """Guarantee at least min_per_prog chunks per programme in multi-programme queries."""
        prog_chunks: Dict[str, List[Tuple[Document, float]]] = {p: [] for p in target_progs}
        general_chunks: List[Tuple[Document, float]] = []

        kept, _ = deduplicate_results(pool)
        for doc, score in kept:
            pname = str(doc.metadata.get("program_name", "") or "")
            if pname in prog_chunks:
                prog_chunks[pname].append((doc, score))
            else:
                general_chunks.append((doc, score))

        selected: List[Tuple[Document, float]] = []
        seen = set()

        # Add min_per_prog chunks per target programme
        for p in target_progs:
            for doc, score in prog_chunks[p][:min_per_prog]:
                key = doc.page_content.strip()[:100]
                if key not in seen:
                    selected.append((doc, score))
                    seen.add(key)

        # Fill remaining slots up to capacity with best chunks
        max_total = max(config.TOP_K, len(target_progs) * min_per_prog + 2)
        remaining = [item for item in kept if item[0].page_content.strip()[:100] not in seen]
        for item in remaining:
            if len(selected) >= max_total:
                break
            selected.append(item)
            seen.add(item[0].page_content.strip()[:100])

        return selected

    def _merge_targeted_pool(
        self,
        pool: List[Tuple[Document, float]],
        targeted: List[Tuple[Document, float]],
    ) -> List[Tuple[Document, float]]:
        """Merge targeted candidates into candidate pool, updating existing chunks with max score."""
        pool_dict: Dict[str, Tuple[Document, float]] = {}
        order: List[str] = []
        for doc, score in pool:
            key = doc.page_content.strip()[:100]
            if key not in pool_dict:
                order.append(key)
                pool_dict[key] = (doc, score)
            else:
                existing_doc, existing_score = pool_dict[key]
                pool_dict[key] = (existing_doc, max(existing_score, score))

        for doc, score in targeted:
            key = doc.page_content.strip()[:100]
            if key in pool_dict:
                existing_doc, existing_score = pool_dict[key]
                pool_dict[key] = (existing_doc, max(existing_score, score))
            else:
                order.append(key)
                pool_dict[key] = (doc, score)

        return [pool_dict[k] for k in order]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        plan: Optional[TurnPlan] = None,
        history: Optional[Any] = None,
    ) -> List[Tuple[Document, float]]:
        self.last_query = query
        if plan is None:
            plan = analyze_turn(query, history=history)

        search_query = plan.standalone_question or query
        keywords = _detect_query_keywords(search_query)
        phrases = _query_phrases(search_query)
        if plan and plan.topic:
            from app.lexicon import get_topic_synonyms
            for syn in get_topic_synonyms(plan.topic)[:4]:
                if syn and syn not in phrases:
                    phrases.append(syn)
        self.last_keywords = keywords
        self.last_phrases = phrases

        is_multi = (plan.is_compare or len(plan.programmes) >= 2) if plan else False
        from app.lexicon import is_topic_programme_independent
        is_prog_independent = is_topic_programme_independent(plan.topic) if plan else False
        explicit_progs = _detect_programmes_in_text(search_query) if search_query else []

        # Programme-independent topics (documents, refund, lms, placement, support, attendance),
        # multi-programme comparisons, or broad queries without explicitly named programmes search across all programmes
        if is_multi or is_prog_independent or (not explicit_progs and plan and plan.is_followup):
            program_name = ""
            intent = INTENT_GENERAL
            pool = self._compare_candidate_search(search_query, plan)
        elif len(plan.programmes) == 1:
            program_name = plan.programmes[0]
            intent = INTENT_PROGRAMME
            pool = self._candidate_search(search_query, program_name, intent=intent, phrases=phrases)
            if plan.topic == "subjects":
                curr_pool = self._curriculum_candidate_search(program_name, plan.year, plan.semester)
                pool = self._merge_targeted_pool(pool, curr_pool)
            elif plan.topic == "specializations":
                spec_pool = self._specialization_candidate_search(program_name)
                pool = self._merge_targeted_pool(pool, spec_pool)
            elif plan.topic in ("fees", "refund", "taxes_hidden_charges", "emi"):
                fee_pool = self._fee_candidate_search(program_name)
                pool = self._merge_targeted_pool(pool, fee_pool)
            elif plan.topic == "faculty":
                fac_pool = self._faculty_candidate_search(program_name)
                pool = self._merge_targeted_pool(pool, fac_pool)
            elif plan.topic == "contact":
                contact_pool = self._contact_candidate_search()
                pool = self._merge_targeted_pool(pool, contact_pool)
        elif _is_programme_overview_query(search_query):
            program_name = ""
            intent = INTENT_OVERVIEW
            pool = self._candidate_search(search_query, "", intent=intent, phrases=phrases)
        else:
            program_name = ""
            intent = INTENT_GENERAL
            pool = self._candidate_search(search_query, "", intent=intent, phrases=phrases)
            if plan and plan.topic == "faculty":
                fac_pool = self._faculty_candidate_search("")
                pool = self._merge_targeted_pool(pool, fac_pool)
            elif plan and plan.topic == "contact":
                contact_pool = self._contact_candidate_search()
                pool = self._merge_targeted_pool(pool, contact_pool)

        self.last_program = program_name
        self.last_intent = intent

        if not pool:
            logger.warning("No candidates retrieved for query: %s", search_query)
            return []

        scored: List[Tuple[Document, float]] = []
        for doc, base_score in pool:
            doc_prog = str(doc.metadata.get("program_name", "") or "")
            final_sc, *_ = _score_chunk(
                doc, base_score, doc_prog or program_name, keywords, phrases,
            )
            scored.append((doc, final_sc))

        scored.sort(key=lambda item: item[1], reverse=True)

        # Apply cross-encoder reranking if available
        if self._reranker and scored:
            try:
                scored = self._reranker.rerank(
                    search_query,
                    scored,
                    top_k=config.RERANKER_TOP_K,
                )
                logger.info("Reranking applied: %d documents reranked", len(scored))
            except Exception as exc:
                logger.warning("Reranking failed: %s", exc)

        if intent == INTENT_OVERVIEW:
            scored = self._overview_boost_and_diversify(scored)
        elif intent == INTENT_GENERAL and not is_multi:
            scored = self._general_diversify(scored)

        # Filter out low-relevance noise below threshold
        relevant_scored = [item for item in scored if item[1] >= getattr(config, "MIN_RELEVANCE_SCORE", 0.52)]
        if not relevant_scored:
            logger.info("All retrieved candidates fell below minimum relevance score threshold (%.2f)", getattr(config, "MIN_RELEVANCE_SCORE", 0.55))
            self.last_pool = []
            return []

        # Keep the full relevant pool for conflict detection
        self.last_pool = relevant_scored

        if is_multi:
            target_progs = plan.programmes if plan.programmes else ALL_PROGRAM_NAMES
            final = self._ensure_multi_program_coverage(relevant_scored, target_progs, min_per_prog=2)
        elif plan.topic in ("subjects", "specializations", "grading", "exams_grading", "faculty"):
            if plan.topic == "faculty":
                relevant_scored = [
                    item for item in relevant_scored
                    if not item[0].page_content.strip().startswith("## Testimonials")
                    and "testimonial" not in str(item[0].metadata.get("source", "")).lower()
                ]
            kept, _removed_dup = deduplicate_results(relevant_scored)
            kept, _removed_div = apply_diversity_cap(kept, max_per_source_page=8)
            top_k = 12 if (plan.topic in ("subjects", "specializations", "grading", "exams_grading", "faculty") and not plan.year and not plan.semester) else config.TOP_K
            final = kept[:top_k]
        else:
            needs_coverage = (
                intent == INTENT_GENERAL
                and not program_name
                and _requires_all_program_coverage(search_query)
            )
            if needs_coverage:
                final = self._all_program_selection(relevant_scored)
            else:
                kept, _removed_dup = deduplicate_results(relevant_scored)
                kept, _removed_div = apply_diversity_cap(kept)
                final = kept[: config.TOP_K]

        # Step 4c: Retrieval rule: for fee questions, the fee-table chunk of every requested programme must be in the context
        if plan and plan.topic in ("fees", "taxes_hidden_charges", "emi"):
            target_progs = plan.programmes if plan.programmes else ALL_PROGRAM_NAMES
            for p in target_progs:
                fee_chunks = self._fee_candidate_search(p)
                for fdoc, fscore in fee_chunks:
                    key = fdoc.page_content.strip()[:100]
                    if not any(d.page_content.strip()[:100] == key for d, _ in final):
                        final.insert(0, (fdoc, max(fscore, 0.90)))

        # Step 4d: Faculty and contact questions: guarantee faculty & contact chunks in the context
        query_lower = search_query.lower()
        if plan and (plan.topic == "faculty" or any(w in query_lower for w in ("faculty", "facult", "professor", "teacher", "who teaches"))):
            fac_chunks = self._faculty_candidate_search(program_name)
            for fdoc, fscore in fac_chunks[:6]:
                key = fdoc.page_content.strip()[:100]
                if not any(d.page_content.strip()[:100] == key for d, _ in final):
                    final.insert(0, (fdoc, max(fscore, 0.92)))

        if plan and (plan.topic == "contact" or any(w in query_lower for w in ("contact", "phone", "email", "helpline", "reach out", "office", "call"))):
            contact_chunks = self._contact_candidate_search()
            for cdoc, cscore in contact_chunks[:4]:
                key = cdoc.page_content.strip()[:100]
                if not any(d.page_content.strip()[:100] == key for d, _ in final):
                    final.insert(0, (cdoc, max(cscore, 0.95)))

        return final


    def _all_program_selection(
        self, pool: List[Tuple[Document, float]],
    ) -> List[Tuple[Document, float]]:
        """Guarantee one chunk per online programme for cross-programmatic
        attribute questions, then fill the remaining top-K slots with the
        best-scoring non-programme chunks."""
        best_by_program: Dict[str, Tuple[Document, float]] = {}
        for doc, score in pool:
            pname = str(doc.metadata.get("program_name", "") or "")
            if pname in ALL_PROGRAM_NAMES:
                if pname not in best_by_program or score > best_by_program[pname][1]:
                    best_by_program[pname] = (doc, score)

        ordered = sorted(pool, key=lambda item: item[1], reverse=True)
        selected: List[Tuple[Document, float]] = [
            best_by_program[p] for p in ALL_PROGRAM_NAMES if p in best_by_program
        ]
        seen = {doc.page_content.strip()[:100] for doc, _ in selected}
        for item in ordered:
            if len(selected) >= config.TOP_K:
                break
            if item[0].page_content.strip()[:100] in seen:
                continue
            selected.append(item)
            seen.add(item[0].page_content.strip()[:100])
        return selected[: config.TOP_K]
