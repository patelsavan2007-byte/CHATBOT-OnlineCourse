"""Cross-encoder reranker for improving retrieval quality.

This module implements reranking using cross-encoder models to improve
the ordering of retrieved chunks beyond simple similarity scores.
Supports both local BGE rerankers and Cohere Rerank API.
"""
from __future__ import annotations

from typing import List, Tuple

from langchain_core.documents import Document

from app.utils import logger


class Reranker:
    """Base class for rerankers."""

    def rerank(
        self,
        query: str,
        documents: List[Tuple[Document, float]],
        top_k: int = 10,
    ) -> List[Tuple[Document, float]]:
        """Rerank documents based on query relevance.

        Args:
            query: Search query
            documents: List of (document, original_score) tuples
            top_k: Number of top results to return

        Returns:
            Reranked list of (document, new_score) tuples
        """
        raise NotImplementedError


class BGEReranker(Reranker):
    """Local BGE cross-encoder reranker using FastEmbed ONNX or FlagEmbedding."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base") -> None:
        """Initialize BGE reranker.

        Args:
            model_name: Model name from HuggingFace
        """
        self.model_name = model_name
        # None  = not yet attempted
        # False = loading failed
        self._model = None
        self.load_error: str | None = None
        self._model_type: str | None = None

    @property
    def model(self):
        """Lazy load the reranker model. Returns None if unavailable."""
        if self._model is None:
            # 1. Try FastEmbed TextCrossEncoder (ONNX runtime, CPU-optimized, runs on any laptop)
            try:
                from fastembed.rerank.cross_encoder import TextCrossEncoder
                logger.info("Loading BGE reranker model via FastEmbed ONNX: %s", self.model_name)
                self._model = TextCrossEncoder(model_name=self.model_name)
                self._model_type = "fastembed"
                self.load_error = None
                logger.info("BGE reranker loaded successfully via FastEmbed ONNX")
                return self._model
            except Exception as exc:
                logger.warning("FastEmbed TextCrossEncoder failed to load (%s): %s", self.model_name, exc)

            # 2. Try FlagEmbedding as secondary fallback
            try:
                from FlagEmbedding import FlagReranker
                logger.info("Loading BGE reranker model via FlagEmbedding: %s", self.model_name)
                self._model = FlagReranker(
                    self.model_name,
                    use_fp16=False,
                )
                self._model_type = "flagembedding"
                self.load_error = None
                logger.info("BGE reranker loaded successfully via FlagEmbedding")
                return self._model
            except ImportError as exc:
                err_msg = (
                    "FlagEmbedding not installed and FastEmbed TextCrossEncoder failed. "
                    "Install with: pip install fastembed or pip install -U FlagEmbedding"
                )
                logger.error("RERANKER LOAD ERROR: %s", err_msg)
                self.load_error = err_msg
                self._model = False
            except Exception as exc:
                err_msg = f"Failed to load BGE reranker ({self.model_name}): {exc}"
                logger.error("RERANKER LOAD ERROR: %s", err_msg)
                self.load_error = err_msg
                self._model = False

        return self._model or None

    def rerank(
        self,
        query: str,
        documents: List[Tuple[Document, float]],
        top_k: int = 10,
    ) -> List[Tuple[Document, float]]:
        """Rerank documents using BGE cross-encoder.

        Args:
            query: Search query
            documents: List of (document, original_score) tuples
            top_k: Number of top results to return

        Returns:
            Reranked list of (document, new_score) tuples
        """
        if not documents:
            return []

        # If reranker model is unavailable, fall back to input ranking
        if self.model is None:
            return documents[:top_k]

        try:
            # Bound candidates to top_k * 2 to keep CPU cross-encoder fast
            candidates = documents[: max(top_k * 2, 20)]
            remaining = documents[len(candidates) :]

            if self._model_type == "fastembed":
                # Truncate text to 600 chars: cross-encoders only need the opening
                # passage to gauge relevance, avoiding quadratic attention slowdowns on long tables
                doc_texts = [doc.page_content[:600] for doc, _ in candidates]
                raw_scores = list(self.model.rerank(query, doc_texts))
            else:
                pairs = [[query, doc.page_content[:600]] for doc, _ in candidates]
                raw_scores = self.model.compute_score(pairs)
                if isinstance(raw_scores, (int, float)):
                    raw_scores = [raw_scores]

            # Combine with original scores (weighted average)
            # Reranker gets higher weight (0.7) vs original score (0.3)
            reranked = []
            for (doc, orig_score), rerank_score in zip(candidates, raw_scores):
                # Normalize rerank score to 0-1 range (typical raw logit range is -10 to 10)
                normalized_rerank = max(0.0, min(1.0, (float(rerank_score) + 10.0) / 20.0))
                combined_score = 0.7 * normalized_rerank + 0.3 * orig_score
                reranked.append((doc, combined_score))

            # Sort by combined score and return top-k
            reranked.sort(key=lambda x: x[1], reverse=True)
            return (reranked + remaining)[:top_k]

        except Exception as exc:
            logger.warning("BGE reranking execution failed: %s", exc)
            return documents[:top_k]


class CohereReranker(Reranker):
    """Cohere Rerank API-based reranker."""

    def __init__(self, api_key: str | None = None, model: str = "rerank-english-v3.0") -> None:
        """Initialize Cohere reranker.

        Args:
            api_key: Cohere API key (or None to read from COHERE_API_KEY env var)
            model: Cohere rerank model name
        """
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load the Cohere client."""
        if self._client is None:
            try:
                import cohere
                import os

                key = self.api_key or os.getenv("COHERE_API_KEY")
                if not key:
                    raise ValueError("COHERE_API_KEY not provided")

                self._client = cohere.Client(api_key=key)
                logger.info("Cohere reranker client initialized")
            except ImportError:
                logger.error("cohere package not installed. Install with: pip install cohere")
                raise
            except Exception as exc:
                logger.error("Failed to initialize Cohere client: %s", exc)
                raise
        return self._client

    def rerank(
        self,
        query: str,
        documents: List[Tuple[Document, float]],
        top_k: int = 10,
    ) -> List[Tuple[Document, float]]:
        """Rerank documents using Cohere Rerank API.

        Args:
            query: Search query
            documents: List of (document, original_score) tuples
            top_k: Number of top results to return

        Returns:
            Reranked list of (document, new_score) tuples
        """
        if not documents:
            return []

        try:
            # Prepare documents for API
            docs = [{"text": doc.page_content} for doc, _ in documents]

            # Call Cohere Rerank API
            response = self.client.rerank(
                model=self.model,
                query=query,
                documents=docs,
                top_n=min(top_k, len(docs)),
                return_documents=True,
            )

            # Extract reranked results
            reranked = []
            for result in response.results:
                doc = documents[result.index][0]
                # Normalize relevance score to 0-1 range
                normalized_score = result.relevance_score / 100.0
                reranked.append((doc, normalized_score))

            return reranked

        except Exception as exc:
            logger.warning("Cohere reranking failed: %s", exc)
            # Fallback to original ranking
            return documents[:top_k]


def create_reranker(
    reranker_type: str = "bge",
    **kwargs,
) -> Reranker:
    """Factory function to create a reranker.

    Args:
        reranker_type: Type of reranker ("bge" or "cohere")
        **kwargs: Additional arguments for the reranker

    Returns:
        Reranker instance
    """
    if reranker_type == "bge":
        return BGEReranker(**kwargs)
    elif reranker_type == "cohere":
        return CohereReranker(**kwargs)
    else:
        raise ValueError(f"Unknown reranker type: {reranker_type}")
