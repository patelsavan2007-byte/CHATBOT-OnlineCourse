from __future__ import annotations

from typing import Any, List

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from app.config import EMBEDDING_MODEL, FALLBACK_EMBEDDING_MODEL, VECTOR_DB_DIR
from app.utils import logger, print_info, print_warning


class FastEmbeddings(Embeddings):
    """Lightweight ONNX-backed embedding generator using FastEmbed.

    Consumes ~80-120 MB RAM instead of 500+ MB with PyTorch.
    Uses the exact same BAAI/bge-small-en-v1.5 model and 384-dim vectors.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model = None

    @property
    def model(self) -> Any:
        if self._model is None:
            from fastembed import TextEmbedding
            print_info(f"Loading FastEmbed (ONNX) model: {self.model_name}")
            logger.info("Loading FastEmbed (ONNX) model: %s", self.model_name)
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = list(self.model.embed(texts))
        return [e.tolist() for e in embeddings]

    def embed_query(self, text: str) -> List[float]:
        embeddings = list(self.model.embed([text]))
        return embeddings[0].tolist()


class EmbeddingStore:
    def __init__(self, persist_directory: str | None = None) -> None:
        self.persist_directory = persist_directory or str(VECTOR_DB_DIR)
        self.embedding_model = self._load_embedding_model()

    def _load_embedding_model(self) -> Embeddings:
        try:
            return FastEmbeddings(model_name=EMBEDDING_MODEL)
        except Exception as exc:
            print_warning(f"FastEmbed unavailable ({exc}); attempting HuggingFace fallback...")
            logger.warning("FastEmbed unavailable (%s); attempting HuggingFace fallback", exc)
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
                print_info(f"Loading embedding model: {EMBEDDING_MODEL}")
                logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
                return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
            except Exception:
                from langchain_huggingface import HuggingFaceEmbeddings
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

