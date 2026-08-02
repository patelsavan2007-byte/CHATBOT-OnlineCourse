"""Verification script to test retriever accuracy on program-specific queries."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.embeddings import EmbeddingStore
from app.retriever import RAGRetriever


def test_retrieval():
    embedding_store = EmbeddingStore()
    vector_store = embedding_store.load_vector_store()
    retriever = RAGRetriever(vector_store)

    test_queries = [
        ("What is the eligibility for Online BCA?", "programs/online_bca.md"),
        ("What is the duration and fee of Online BBA?", "programs/online_bba.md"),
        ("What is the curriculum for Online MBA?", "programs/online_mba.md"),
        ("Tell me about Online MCA admission requirements", "programs/online_mca.md"),
    ]

    all_passed = True
    print("\n--- Testing RAG Retriever Program Filtering ---\n")

    for query, expected_source in test_queries:
        print(f"Query: '{query}'")
        results = retriever.retrieve(query)
        retrieved_sources = [doc.metadata.get("source") for doc, _ in results]
        primary_source = retrieved_sources[0] if retrieved_sources else None

        print(f"  Primary Retrieved Document: {primary_source}")
        print(f"  Expected Document: {expected_source}")

        if primary_source == expected_source:
            print("  [PASSED]\n")
        else:
            print(f"  [FAILED] All retrieved sources: {retrieved_sources}\n")
            all_passed = False

    if all_passed:
        print("SUCCESS: All program queries correctly retrieved their dedicated markdown document!")
    else:
        print("WARNING: Some queries did not match the expected primary document.")


if __name__ == "__main__":
    test_retrieval()
