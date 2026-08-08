"""Retrieval-only verification: programme filtering, ranking and diversity.

No Gemini API access is required. These tests exercise the retriever directly
so failures here reflect retrieval quality, not LLM/API availability.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.embeddings import EmbeddingStore
from app.retriever import RAGRetriever


def _expected_program_sources() -> dict:
    return {
        "online_bca": ["pdfs/PPR_Online BCA.pdf", "programs/online_bca.md"],
        "online_bba": ["pdfs/PPR_Online BBA.pdf", "programs/online_bba.md"],
        "online_mba": ["pdfs/PPR_Online MBA.pdf", "programs/online_mba.md"],
        "online_mca": ["pdfs/PPR_Online MCA.pdf", "programs/online_mca.md"],
    }


def test_retrieval() -> None:
    embedding_store = EmbeddingStore()
    vector_store = embedding_store.load_vector_store()
    retriever = RAGRetriever(vector_store)

    test_queries = [
        ("What is the eligibility for Online BCA?", "online_bca"),
        ("What is the duration and fee of Online BBA?", "online_bba"),
        ("What is the curriculum for Online MBA?", "online_mba"),
        ("Tell me about Online MCA admission requirements", "online_mca"),
        ("What is the refund policy?", None),
    ]

    expected = _expected_program_sources()
    all_passed = True
    print("\n--- Testing RAG Retriever Programme Filtering ---\n")

    for query, program in test_queries:
        print(f"Query: '{query}'")
        results = retriever.retrieve(query)
        retrieved_sources = [doc.metadata.get("source") for doc, _ in results]

        if not retrieved_sources:
            print("  [FAILED] No results retrieved\n")
            all_passed = False
            continue

        print(f"  Detected programme: {retriever.last_program!r}")
        for doc, score in results:
            print(f"    {score:.3f}  {doc.metadata.get('source')} | page {doc.metadata.get('page', 'n/a')}")

        if program:
            candidates = expected[program]
            primary = retrieved_sources[0]
            if primary in candidates:
                print(f"  [PASSED] Primary source {primary} matches {program}\n")
            else:
                print(f"  [FAILED] Primary {primary} not in expected {candidates}; all: {retrieved_sources}\n")
                all_passed = False
        else:
            refund_sources = ["pdfs/Fees Refund Policy.pdf", "terms-conditions.md"]
            matched = [s for s in refund_sources if s in retrieved_sources]
            if matched:
                print(f"  [PASSED] Refund policy sources found: {matched}\n")
            else:
                print(f"  [FAILED] Refund sources not found; all: {retrieved_sources}\n")
                all_passed = False

    # Diversity: no single (source, page) may dominate the top-K.
    print("\n--- Testing Diversity Cap ---")
    results = retriever.retrieve("What is the total MBA programme fee?")
    from collections import Counter
    page_counts = Counter((d.metadata.get("source"), d.metadata.get("page")) for d, _ in results)
    dominant = page_counts.most_common(1)[0]
    if dominant[1] > 2:
        print(f"  [FAILED] A single source/page dominates the top-K: {dominant}")
        all_passed = False
    else:
        print(f"  [PASSED] Top-K spread across pages (max {dominant[1]} per source/page)")

    if all_passed:
        print("SUCCESS: All retrieval checks passed!")
    else:
        print("WARNING: Some retrieval checks did not pass.")


if __name__ == "__main__":
    test_retrieval()
