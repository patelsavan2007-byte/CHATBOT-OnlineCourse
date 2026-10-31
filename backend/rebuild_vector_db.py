#!/usr/bin/env python3
"""Rebuild vector database chunks from knowledge base markdown files."""

from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.ingestion import KnowledgeBaseIngester
from app.embeddings import EmbeddingStore
from app.utils import print_info, print_warning, print_error
from app.config import VECTOR_DB_DIR


def main():
    print_info("=" * 60)
    print_info("Rebuilding Vector Database from Knowledge Base")
    print_info("=" * 60)

    # Step 1: Load documents
    print_info("\n[1/4] Loading markdown documents from knowledge base...")
    ingester = KnowledgeBaseIngester()

    # Reset and clean up old vector database
    print_info("Cleaning up old vector database...")
    ingester.reset_vector_store()

    # Load all documents
    documents = ingester.load_documents()
    print_info(f"Loaded {len(documents)} documents")

    # Step 2: Split documents into chunks
    print_info("\n[2/4] Splitting documents into chunks...")
    chunks = ingester.split_documents(documents)
    print_info(f"Created {len(chunks)} chunks")

    # Step 3: Build source manifest
    print_info("\n[3/4] Building source manifest...")
    ingester.write_source_manifest()
    print_info("Source manifest written")

    # Step 4: Build vector database
    print_info("\n[4/4] Building vector database with embeddings...")
    store = EmbeddingStore(persist_directory=str(VECTOR_DB_DIR))
    vector_store = store.build_vector_store(chunks)
    print_info("Vector database built and persisted")

    print_info("\n" + "=" * 60)
    print_info("Vector database rebuild complete!")
    print_info(f"Total chunks: {len(chunks)}")
    print_info(f"Database location: {VECTOR_DB_DIR}")
    print_info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())