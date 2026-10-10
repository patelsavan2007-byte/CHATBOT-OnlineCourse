"""Rebuild the ChromaDB vector store from the freshly scraped knowledge base."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ensure_directories
from app.embeddings import EmbeddingStore
from app.ingestion import KnowledgeBaseIngester
from app.utils import print_info


def main() -> None:
    ensure_directories()
    ingester = KnowledgeBaseIngester()

    # Load documents from the freshly scraped knowledge base
    documents = ingester.load_documents()
    print_info(f"Documents loaded: {len(documents)}")
    for doc in documents:
        src = doc.metadata.get("source", "unknown")
        prog = doc.metadata.get("program_name", "")
        label = f" (program: {prog})" if prog else ""
        print_info(f"  - {src}{label}")

    # Chunk documents
    chunks = ingester.split_documents(documents)

    # Reset and rebuild vector store with Markdown documents
    ingester.reset_vector_store()
    embedding_store = EmbeddingStore()
    vector_store = embedding_store.build_vector_store(chunks)
    ingester.write_source_manifest()

    # Ingest PDF documents into the newly built vector store
    from app.pdf_ingestion import ingest_pdfs_to_vectordb
    pdf_chunks_count = ingest_pdfs_to_vectordb()

    total_chunks = len(chunks) + pdf_chunks_count
    print_info("")
    print_info("=" * 50)
    print_info(f"Markdown Files Loaded: {len(documents)}")
    print_info(f"Markdown Chunks: {len(chunks)}")
    print_info(f"PDF Chunks Added: {pdf_chunks_count}")
    print_info(f"Total Chunks Generated: {total_chunks}")
    print_info("ChromaDB Rebuilt Successfully")
    print_info("=" * 50)


if __name__ == "__main__":
    main()
