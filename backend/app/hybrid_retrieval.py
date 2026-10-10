"""Hybrid retrieval combining semantic embeddings with BM25 keyword search using RRF fusion.

This module implements hybrid retrieval that:
1. Performs semantic search using vector embeddings
2. Performs keyword search using BM25
3. Fuses results using Reciprocal Rank Fusion (RRF)
4. Provides improved retrieval for both semantic and keyword-oriented queries
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.utils import logger


# RRF constant - lower value gives more weight to high-ranked documents
RRF_K = 60


def _metadata_matches(metadata: dict, filter: dict) -> bool:
    """Return True if document metadata satisfies the Chroma-style filter dict.

    Supports:
    - {key: value}       exact match
    - {key: {"$in": [...]}} list membership
    - {"$or": [...]}     any sub-filter matches
    """
    if not filter:
        return True
    if "$or" in filter:
        return any(_metadata_matches(metadata, sub) for sub in filter["$or"])
    for key, condition in filter.items():
        if key.startswith("$"):
            continue
        val = metadata.get(key)
        if isinstance(condition, dict):
            if "$in" in condition:
                if val not in condition["$in"]:
                    return False
            else:
                return False  # unknown operator — skip conservatively
        else:
            if val != condition:
                return False
    return True


def tokenize(text: str) -> List[str]:
    """Simple tokenization for BM25 indexing."""
    import re
    # Extract alphanumeric tokens, convert to lowercase
    tokens = re.findall(r"\b[a-z0-9']+\b", text.lower())
    return tokens


class HybridRetriever:
    """Hybrid retriever combining semantic and keyword search with RRF fusion."""

    def __init__(self, vector_store: Chroma, documents: List[Document]) -> None:
        """Initialize hybrid retriever with vector store and document corpus.

        Args:
            vector_store: Chroma vector store for semantic search
            documents: List of all documents for BM25 indexing
        """
        self.vector_store = vector_store
        self.documents = documents

        # Build BM25 index
        logger.info("Building BM25 index for hybrid retrieval...")
        tokenized_docs = [tokenize(doc.page_content) for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)
        logger.info("BM25 index built with %d documents", len(documents))

        # Create mapping from document index to Document object
        self.doc_index_map: Dict[int, Document] = {i: doc for i, doc in enumerate(documents)}

    def semantic_search(
        self,
        query: str,
        k: int = 20,
        filter: Dict | None = None,
    ) -> List[Tuple[Document, float]]:
        """Perform semantic search using vector embeddings.

        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of (document, score) tuples
        """
        try:
            results = self.vector_store.similarity_search_with_relevance_scores(
                query, k=k, filter=filter
            )
            return results
        except Exception as exc:
            logger.warning("Semantic search failed: %s", exc)
            return []

    def keyword_search(
        self,
        query: str,
        k: int = 20,
        filter: Dict | None = None,
    ) -> List[Tuple[Document, float]]:
        """Perform keyword search using BM25.

        Applies the same metadata filter as semantic_search so that
        programme-scoped queries do not receive chunks from other programmes
        via the BM25 path.

        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter (same format as semantic_search)

        Returns:
            List of (document, score) tuples
        """
        try:
            tokenized_query = tokenize(query)
            doc_scores = self.bm25.get_scores(tokenized_query)

            # Determine candidate order by BM25 score
            ranked_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)

            # Apply metadata filter (same logic as Chroma's filter)
            if filter:
                ranked_indices = [
                    i for i in ranked_indices
                    if _metadata_matches(self.doc_index_map[i].metadata, filter)
                ]

            top_indices = ranked_indices[:k]

            max_score = float(doc_scores.max()) if len(doc_scores) > 0 else 1.0
            if max_score == 0.0:
                max_score = 1.0

            results = []
            for idx in top_indices:
                doc = self.doc_index_map[idx]
                # Normalize BM25 score to 0-1 range for consistency
                normalized_score = min(doc_scores[idx] / max_score, 1.0)
                results.append((doc, normalized_score))

            return results
        except Exception as exc:
            logger.warning("Keyword search failed: %s", exc)
            return []

    def rrf_fusion(
        self,
        semantic_results: List[Tuple[Document, float]],
        keyword_results: List[Tuple[Document, float]],
        k: int = 20,
    ) -> List[Tuple[Document, float]]:
        """Fuse semantic and keyword results using Reciprocal Rank Fusion.

        RRF formula: rank_score = sum(1 / (RRF_K + rank)) for each list.
        RRF is used ONLY for ordering.  The returned score for each document
        is its original semantic-similarity score (0-1 cosine range) so that
        the downstream MIN_RELEVANCE_SCORE threshold operates on a meaningful
        scale.  Documents that appear only in BM25 (no semantic result) receive
        a floor score of BM25_ONLY_FLOOR so they can reach the reranker but are
        below the semantic relevance bar by default.
        """
        BM25_ONLY_FLOOR = 0.30  # below MIN_RELEVANCE_SCORE but above total noise

        # Build semantic score lookup keyed by content prefix
        sem_score_map: Dict[str, float] = {}
        for doc, score in semantic_results:
            doc_id = doc.page_content.strip()[:100]
            sem_score_map[doc_id] = max(sem_score_map.get(doc_id, 0.0), score)

        # Compute RRF rank scores for ordering
        rrf_rank: Dict[str, float] = {}
        for rank, (doc, _) in enumerate(semantic_results):
            doc_id = doc.page_content.strip()[:100]
            rrf_rank[doc_id] = rrf_rank.get(doc_id, 0.0) + 1.0 / (RRF_K + rank + 1)
        for rank, (doc, _) in enumerate(keyword_results):
            doc_id = doc.page_content.strip()[:100]
            rrf_rank[doc_id] = rrf_rank.get(doc_id, 0.0) + 1.0 / (RRF_K + rank + 1)

        # Build document map (first occurrence wins)
        doc_map: Dict[str, Document] = {}
        for doc, _ in semantic_results + keyword_results:
            doc_id = doc.page_content.strip()[:100]
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        # Sort by RRF rank score but return the semantic similarity as the score
        sorted_ids = sorted(rrf_rank.keys(), key=lambda x: rrf_rank[x], reverse=True)
        fused_results = [
            (doc_map[doc_id], sem_score_map.get(doc_id, BM25_ONLY_FLOOR))
            for doc_id in sorted_ids
            if doc_id in doc_map
        ]

        return fused_results[:k]

    def hybrid_search(
        self,
        query: str,
        k: int = 20,
        filter: Dict | None = None,
    ) -> List[Tuple[Document, float]]:
        """Perform hybrid search combining semantic and keyword approaches.

        The filter is now applied to BOTH semantic and keyword search so that
        programme-scoped queries only receive chunks from the correct programme.

        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter applied to both semantic and keyword search

        Returns:
            Fused and ranked list of (document, score) tuples, scored on the
            semantic similarity scale (0-1) for downstream threshold compatibility.
        """
        # Get results from both approaches – fetch wider semantic pool so candidates get true semantic scores
        semantic_results = self.semantic_search(query, k=max(k * 2, 40), filter=filter)
        keyword_results = self.keyword_search(query, k=k, filter=filter)

        # Fuse using RRF (ordering only); scores come from semantic similarity
        fused_results = self.rrf_fusion(semantic_results, keyword_results, k=k)

        logger.info(
            "Hybrid search: %d semantic + %d keyword -> %d fused results",
            len(semantic_results),
            len(keyword_results),
            len(fused_results),
        )

        return fused_results
