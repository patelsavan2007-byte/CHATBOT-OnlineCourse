from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
 
from app.config import ensure_directories
from app.embeddings import EmbeddingStore
from app.ingestion import KnowledgeBaseIngester


if __name__ == "__main__":
    ensure_directories()
    ingester = KnowledgeBaseIngester()
    documents = ingester.load_documents()
    chunks = ingester.split_documents(documents)
    ingester.reset_vector_store()
    embedding_store = EmbeddingStore()
    embedding_store.build_vector_store(chunks)
