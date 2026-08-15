"""RAG Pipeline Evaluation — Per-question timing, retrieval scores and answer quality.

Run from the project root:
    python backend/eval_rag.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ensure_directories
from app.embeddings import EmbeddingStore
from app.llm import LLMClient
from app.rag_chain import RAGChain
from app.retriever import RAGRetriever

TEST_QUESTIONS = [
    "What is the duration of BBA?",
    "What is the BBA fee structure?",
    "What is the BCA programme about?",
    "Is the online degree recognized by UGC?",
    "How are examinations conducted?",
    "Is technical support available?",
    "Will I receive a degree certificate after completion?",
    "What programmes are offered?",
    "What is the eligibility for Online BCA?",
    "How do I apply for admission?",
    "Can I pay the fees in installments?",
    "What is the refund policy?",
    "Are the classes online?",
    "Is there placement assistance?",
    "How can I contact the university?",
    "What is the total fee of MBA?",
    "What are the specializations in MBA?",
    "What is the admission process for MCA?",
    "How many credits are in the BBA programme?",
    "Is there any scholarship or financial aid?",
    "What documents are required for admission?",
    "What is the examination fee?",
    "Does the university offer counselling?",
    "What is the GDP of India?",  # NOT in knowledge base
]


def evaluate() -> list[dict]:
    ensure_directories()

    # Bootstrap
    t0 = time.time()
    embedding_store = EmbeddingStore()
    vector_store = embedding_store.load_vector_store()
    retriever = RAGRetriever(vector_store)
    llm_client = LLMClient()
    rag_chain = RAGChain(retriever, llm_client)
    startup_time = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  RAG Pipeline Evaluation")
    print(f"  Startup time: {startup_time:.2f}s")
    print(f"{'='*70}\n")

    results = []

    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"\n--- Q{i}: {question}")

        # Retrieval
        t_ret = time.time()
        retrieved = retriever.retrieve(question)
        retrieval_time = time.time() - t_ret

        # Collect retrieval info
        chunks_info = []
        for doc, score in retrieved:
            chunks_info.append({
                "source": doc.metadata.get("source", "unknown"),
                "page": doc.metadata.get("page"),
                "score": round(score, 4),
                "snippet": doc.page_content[:80].replace("\n", " "),
            })

        # Full RAG answer
        t_llm = time.time()
        answer_text, answer_retrieved = rag_chain.answer(question)
        llm_time = time.time() - t_llm
        total_time = retrieval_time + llm_time

        result = {
            "question": question,
            "retrieval_time_s": round(retrieval_time, 3),
            "llm_time_s": round(llm_time, 3),
            "total_time_s": round(total_time, 3),
            "num_chunks": len(retrieved),
            "chunks": chunks_info,
            "llm_status": rag_chain.last_status,
            "answer_len": len(answer_text),
            "answer_preview": answer_text[:200].replace("\n", " "),
            "has_not_found": "couldn't find" in answer_text.lower() or "could not find" in answer_text.lower(),
            "has_sources_in_answer": "source:" in answer_text.lower(),
        }
        results.append(result)

        # Print summary
        scores = [c["score"] for c in chunks_info]
        sources = [c["source"] for c in chunks_info]
        print(f"  Retrieval: {retrieval_time:.3f}s | {len(retrieved)} chunks | scores: {scores}")
        print(f"  Sources: {sources}")
        print(f"  LLM: {llm_time:.3f}s | status: {rag_chain.last_status}")
        print(f"  Total: {total_time:.3f}s")
        print(f"  Not-found: {result['has_not_found']} | Answer len: {len(answer_text)}")
        print(f"  Answer: {answer_text[:150].replace(chr(10), ' ')}")

    # Summary table
    print(f"\n\n{'='*70}")
    print(f"  EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"{'Q#':<4} {'Time':>6} {'Ret':>6} {'LLM':>6} {'#Ch':>4} {'Scores':>20} {'NotFound':>9} {'Status':>8}")
    print("-" * 70)
    for i, r in enumerate(results, 1):
        scores_str = ",".join(f"{c['score']:.2f}" for c in r["chunks"][:3])
        print(
            f"Q{i:<3} {r['total_time_s']:>5.1f}s {r['retrieval_time_s']:>5.2f}s "
            f"{r['llm_time_s']:>5.1f}s {r['num_chunks']:>4} {scores_str:>20} "
            f"{'YES' if r['has_not_found'] else 'no':>9} {r['llm_status']:>8}"
        )

    avg_total = sum(r["total_time_s"] for r in results) / len(results)
    avg_ret = sum(r["retrieval_time_s"] for r in results) / len(results)
    avg_llm = sum(r["llm_time_s"] for r in results) / len(results)
    not_found_count = sum(1 for r in results if r["has_not_found"])
    print("-" * 70)
    print(f"AVG  {avg_total:>5.1f}s {avg_ret:>5.2f}s {avg_llm:>5.1f}s")
    print(f"Not-found responses: {not_found_count}/{len(results)}")
    print(f"{'='*70}\n")

    return results


if __name__ == "__main__":
    results = evaluate()
    # Save results to JSON for comparison
    out = ROOT / "eval_results.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {out}")
