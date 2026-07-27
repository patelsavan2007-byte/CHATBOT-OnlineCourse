from __future__ import annotations

from typing import List, Tuple

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

from app.config import TOP_K
from app.utils import logger, print_info


class RAGRetriever:
    def __init__(self, vector_store: Chroma) -> None:
        self.vector_store = vector_store

    def retrieve(self, query: str) -> List[Tuple[Document, float]]:
        results = self.vector_store.similarity_search_with_relevance_scores(query, k=TOP_K)
        print_info(f"Retrieved chunks: {len(results)}")
        logger.info("Retrieved chunks: %s", len(results))
        for document, score in results:
            logger.info("Chunk score %.3f from %s", score, document.metadata.get("source", "unknown"))
        return results
