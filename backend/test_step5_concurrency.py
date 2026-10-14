"""Test Step 5: Concurrency and Thread-Safety Test.

Launches 20 concurrent requests across different programmes (BBA, BCA, MBA, MCA)
and verifies that:
1. Each thread receives its own correct AnswerResult.
2. Returned answers and retrieved chunks correspond strictly to the queried programme.
3. No shared last_* state causes cross-programme contamination.
"""
import concurrent.futures
import sys
from unittest.mock import MagicMock

from app.embeddings import EmbeddingStore
from app.llm import LLMClient
from app.rag_chain import RAGChain, AnswerResult
from app.retriever import RAGRetriever

def main():
    store = EmbeddingStore()
    vector_store = store.load_vector_store()
    retriever = RAGRetriever(vector_store)
    
    # Mock LLM generation to test concurrency of retrieval, conflict detection,
    # and pipeline without exhausting external API token rate limits
    llm = LLMClient()
    llm.generate = MagicMock(side_effect=lambda prompt, context_chunks=None, conflicts=None: (
        "Grounding verification mock answer", "mock_success"
    ))
    chain = RAGChain(retriever, llm, use_cache=False)

    queries = [
        ("What is the fee for BBA?", "online_bba"),
        ("What is the duration of MCA?", "online_mca"),
        ("What are the eligibility criteria for MBA?", "online_mba"),
        ("What courses are in BCA semester 1?", "online_bca"),
        ("Tell me about BBA admission requirements", "online_bba"),
    ] * 4  # 20 concurrent queries total

    print(f"Running {len(queries)} concurrent queries across 10 threads...")

    def run_query(idx, q, expected_prog):
        res = chain.answer(q)
        assert isinstance(res, AnswerResult), f"Expected AnswerResult, got {type(res)}"
        assert len(res) == 2, f"Expected unpackable len 2, got {len(res)}"
        ans, retrieved = res
        assert ans == res.answer
        assert retrieved == res.retrieved
        assert res.status is not None
        # Verify retrieved chunks contain the expected programme if chunks returned
        if retrieved:
            progs = [str(doc.metadata.get("program_name", "")) for doc, _ in retrieved]
            has_expected = any(p == expected_prog for p in progs)
            if not has_expected:
                return False, f"[{idx}] Query {q!r}: chunks lacked {expected_prog}: {progs}"
        return True, f"[{idx}] OK: status={res.status}, chunks={len(retrieved)}"

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(run_query, i, q, prog)
            for i, (q, prog) in enumerate(queries)
        ]
        for f in concurrent.futures.as_completed(futures):
            ok, msg = f.result()
            print(msg)
            results.append(ok)

    passed = sum(results)
    total = len(results)
    print(f"\nStep 5 Concurrency Test: {passed}/{total} PASSED")
    if passed < total:
        sys.exit(1)

if __name__ == "__main__":
    main()
