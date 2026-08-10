from __future__ import annotations

from typing import Any

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import EMBEDDING_MODEL, FALLBACK_EMBEDDING_MODEL, VECTOR_DB_DIR
from app.utils import logger, print_info


class EmbeddingStore:
    def __init__(self, persist_directory: str | None = None) -> None:
        self.persist_directory = persist_directory or str(VECTOR_DB_DIR)
        self.embedding_model = self._load_embedding_model()

    def _load_embedding_model(self) -> HuggingFaceEmbeddings:
        try:
            print_info(f"Loading embedding model: {EMBEDDING_MODEL}")
            logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
            return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        except Exception:
            print_info(f"Falling back to embedding model: {FALLBACK_EMBEDDING_MODEL}")
            logger.warning("Primary embedding model unavailable; using fallback")
            return HuggingFaceEmbeddings(model_name=FALLBACK_EMBEDDING_MODEL)

    def build_vector_store(self, documents: list[Any]) -> Chroma:
        print_info("Creating Chroma vector database...")
        logger.info("Creating Chroma vector database")
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embedding_model,
            persist_directory=self.persist_directory,
        )
        if hasattr(vector_store, "persist"):
            vector_store.persist()
        print_info("Database saved successfully.")
        logger.info("Database saved successfully")
        return vector_store

    def load_vector_store(self) -> Chroma:
        print_info("Loading existing Chroma vector database...")
        logger.info("Loading existing Chroma vector database")
        return Chroma(persist_directory=self.persist_directory, embedding_function=self.embedding_model)

    def add_documents(self, documents: list[Any], vector_store: Chroma | None = None) -> Chroma:
        """Add documents to an existing vector store without rebuilding.

        This allows PDF chunks to be added alongside website chunks
        without destroying the existing data.
        """
        store = vector_store or self.load_vector_store()
        print_info(f"Adding {len(documents)} documents to existing vector store...")
        logger.info("Adding %d documents to existing vector store", len(documents))
        store.add_documents(documents)
        if hasattr(store, "persist"):
            store.persist()
        print_info("Documents added and persisted successfully.")
        logger.info("Documents added and persisted successfully")
        return store
