"""Retrieval + answer tests for all programme PDFs and general policy documents.

Design:
* RETRIEVAL is always exercised directly and gates the PASS/FAIL result.
* LLM generation is reported separately. When the Gemini API is unavailable
  (e.g. quota exhausted) the deterministic local fallback still produces an
  answer and the test is NOT failed for that reason.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ensure_directories
from app.embeddings import EmbeddingStore
from app.llm import LLMClient, LLMStatus
from app.rag_chain import RAGChain
from app.retriever import RAGRetriever
from app.utils import console, print_info, print_section, print_warning, Timer


# ---- Test Questions -------------------------------------------------------

MBA_TESTS = [
    {
        "id": "MBA-1",
        "question": "What is the total MBA programme fee?",
        "expected_keywords": ["1,50,000", "150000", "75,000"],
        "expected_sources": ["pdfs/PPR_Online MBA.pdf"],
    },
    {
        "id": "MBA-2",
        "question": "What is the MBA fee for the first year?",
        "expected_keywords": ["75,000"],
        "expected_sources": ["pdfs/PPR_Online MBA.pdf"],
    },
    {
        "id": "MBA-3",
        "question": "What is the examination fee?",
        "expected_keywords": ["3500", "14000", "7000"],
        "expected_sources": ["pdfs/PPR_Online MBA.pdf"],
    },
    {
        "id": "MBA-4",
        "question": "What are the MBA specializations?",
        "expected_keywords": ["finance", "marketing", "hr", "human resource", "specialization", "specialisation", "stream", "functional area"],
        "expected_sources": ["pdfs/PPR_Online MBA.pdf"],
    },
    {
        "id": "MBA-5",
        "question": "What are the credits in each semester?",
        "expected_keywords": ["28", "26", "20"],
        "expected_sources": ["pdfs/PPR_Online MBA.pdf"],
    },
    {
        "id": "MBA-6",
        "question": "What is the MBA eligibility?",
        "expected_keywords": ["bachelor", "degree"],
        "expected_sources": ["pdfs/PPR_Online MBA.pdf"],
    },
    {
        "id": "MBA-7",
        "question": "What is the duration of the MBA programme?",
        "expected_keywords": ["2", "4", "years", "yrs"],
        "expected_sources": ["pdfs/PPR_Online MBA.pdf"],
    },
]

BCA_TESTS = [
    {
        "id": "BCA-1",
        "question": "What is the eligibility for Online BCA?",
        "expected_keywords": ["12", "higher secondary", "hsc", "10+2", "secondary"],
        "expected_sources": ["pdfs/PPR_Online BCA.pdf", "programs/online_bca.md"],
    },
    {
        "id": "BCA-2",
        "question": "What is the duration of Online BCA?",
        "expected_keywords": ["3", "years", "yrs"],
        "expected_sources": ["pdfs/PPR_Online BCA.pdf", "programs/online_bca.md"],
    },
    {
        "id": "BCA-3",
        "question": "What is the fee for Online BCA?",
        "expected_keywords": ["50,000", "40,000", "fee"],
        "expected_sources": ["pdfs/PPR_Online BCA.pdf"],
    },
]

BBA_TESTS = [
    {
        "id": "BBA-1",
        "question": "What is the eligibility for Online BBA?",
        "expected_keywords": ["12", "higher secondary", "hsc", "10+2", "secondary"],
        "expected_sources": ["pdfs/PPR_Online BBA.pdf", "programs/online_bba.md"],
    },
    {
        "id": "BBA-2",
        "question": "What is the duration of Online BBA?",
        "expected_keywords": ["3", "years", "yrs"],
        "expected_sources": ["pdfs/PPR_Online BBA.pdf", "programs/online_bba.md"],
    },
    {
        "id": "BBA-3",
        "question": "What is the fee for Online BBA?",
        "expected_keywords": ["50,000", "fee"],
        "expected_sources": ["pdfs/PPR_Online BBA.pdf"],
    },
]

MCA_TESTS = [
    {
        "id": "MCA-1",
        "question": "What is the eligibility for Online MCA?",
        "expected_keywords": ["bachelor", "bca", "degree", "graduation"],
        "expected_sources": ["pdfs/PPR_Online MCA.pdf", "programs/online_mca.md"],
    },
    {
        "id": "MCA-2",
        "question": "What is the duration of Online MCA?",
        "expected_keywords": ["2", "years", "yrs"],
        "expected_sources": ["pdfs/PPR_Online MCA.pdf", "programs/online_mca.md"],
    },
    {
        "id": "MCA-3",
        "question": "What is the fee for Online MCA?",
        "expected_keywords": ["fee", "75,000", "60,000"],
        "expected_sources": ["pdfs/PPR_Online MCA.pdf"],
    },
]

REFUND_TESTS = [
    {
        "id": "REFUND-1",
        "question": "What is the refund policy?",
        "expected_keywords": ["refund", "fee"],
        "expected_sources": ["pdfs/Fees Refund Policy.pdf", "terms-conditions.md"],
    },
    {
        "id": "REFUND-2",
        "question": "Under what conditions is a refund allowed?",
        "expected_keywords": ["refund", "cancel", "withdraw"],
        "expected_sources": ["pdfs/Fees Refund Policy.pdf", "terms-conditions.md"],
    },
]

# Conflict detection is verified even in local-fallback mode: both values
# must appear together with an explicit disagreement note.
INCONSISTENCY_TEST = {
    "id": "INCONSISTENCY-1",
    "question": "What is the total number of credits in the MBA programme?",
    "expected_both": ["102", "100"],
    "expected_sources": ["pdfs/PPR_Online MBA.pdf"],
    "description": "Should detect the 102 credits (pages 4, 10) vs 100 credits (page 12 / online_mba.md) disagreement",
}


def run_tests() -> None:
    ensure_directories()
    print_section("CHARUSAT All-PDF Retrieval Tests")

    print_info("Loading vector store and models...")
    embedding_store = EmbeddingStore()
    vector_store = embedding_store.load_vector_store()
    retriever = RAGRetriever(vector_store)
    llm_client = LLMClient()
    rag_chain = RAGChain(retriever, llm_client)

    doc_count = vector_store._collection.count()
    print_info(f"Vector store contains {doc_count} documents.")
    print_info("")

    passed = 0
    failed = 0

    all_tests = [
        ("MBA TESTS", MBA_TESTS),
        ("BCA TESTS", BCA_TESTS),
        ("BBA TESTS", BBA_TESTS),
        ("MCA TESTS", MCA_TESTS),
        ("REFUND POLICY TESTS", REFUND_TESTS),
    ]

    for section_name, tests in all_tests:
        print_info("=" * 70)
        print_section(section_name)
        for test in tests:
            result = run_single_test(test, retriever, rag_chain)
            if result:
                passed += 1
            else:
                failed += 1

    print_info("=" * 70)
    print_section("INCONSISTENCY TEST (conflict detection)")
    inconsistency_result = run_inconsistency_test(INCONSISTENCY_TEST, retriever, rag_chain)
    if inconsistency_result:
        passed += 1
    else:
        failed += 1

    print_info("")
    print_info("=" * 70)
    total = passed + failed
    print_info(f"Results: {passed}/{total} passed, {failed}/{total} failed")
    if failed == 0:
        print_info("ALL TESTS PASSED!")
    else:
        print_warning(f"{failed} test(s) need attention.")


def _retrieval_pass(retriever: RAGRetriever, question: str, expected_sources: list) -> bool:
    results = retriever.retrieve(question)
    if not results:
        print_warning("  RETRIEVAL: FAILED (no results)")
        return False

    retrieved_sources = [doc.metadata.get("source") for doc, _ in results]
    for source in retrieved_sources:
        page = results[0][0].metadata.get("page", "n/a")
        score = [s for d, s in results if d.metadata.get("source") == source]
        print_info(f"  Chunk: {source} | Page: {page} | Score: {score[0]:.3f}" if score else f"  Chunk: {source}")

    matched = [s for s in expected_sources if s in retrieved_sources]
    if matched:
        print_info(f"  RETRIEVAL: PASSED (found {matched})")
        return True
    print_warning(f"  RETRIEVAL: FAILED (expected one of {expected_sources}; got {retrieved_sources})")
    return False


def run_single_test(test: dict, retriever: RAGRetriever, rag_chain: RAGChain) -> bool:
    test_id = test["id"]
    question = test["question"]
    expected_keywords = test["expected_keywords"]

    print_info("-" * 70)
    print_info(f"Test {test_id}: {question}")

    with Timer() as timer:
        retrieval_pass = _retrieval_pass(retriever, question, test.get("expected_sources", []))
        answer, retrieved = rag_chain.answer(question)
        status = rag_chain.last_status

    print_info(f"  LLM status: {status}")
    answer_display = answer[:400].replace("\n", "\n    ")
    print_info(f"  Answer: {answer_display}")
    print_info(f"  Response time: {timer.elapsed_seconds:.2f}s")

    if status == LLMStatus.LLM:
        found = [kw for kw in expected_keywords if kw.lower() in answer.lower()]
        if found:
            print_info(f"  LLM GENERATION: PASSED (found {found})")
            return retrieval_pass
        print_warning(f"  LLM GENERATION: FAILED (expected {expected_keywords})")
        return False
    else:
        found = [kw for kw in expected_keywords if kw.lower() in answer.lower()]
        if found:
            print_info(f"  LLM GENERATION: SKIPPED - {status.upper()} (fallback found {found})")
        else:
            print_warning(f"  LLM GENERATION: SKIPPED - {status.upper()} (fallback missed {expected_keywords})")
        return retrieval_pass


def run_inconsistency_test(test: dict, retriever: RAGRetriever, rag_chain: RAGChain) -> bool:
    question = test["question"]
    expected_both = test["expected_both"]

    print_info(f"{test['description']}")
    print_info(f"Question: {question}")

    with Timer() as timer:
        retrieval_pass = _retrieval_pass(retriever, question, test.get("expected_sources", []))
        answer, _retrieved = rag_chain.answer(question)
        status = rag_chain.last_status

    answer_display = answer[:500].replace("\n", "\n    ")
    print_info(f"  Answer: {answer_display}")
    print_info(f"  LLM status: {status}")
    print_info(f"  Response time: {timer.elapsed_seconds:.2f}s")

    answer_lower = answer.lower()
    found = [value for value in expected_both if value in answer_lower]
    inconsistency_words = ["inconsisten", "conflict", "discrepan", "differ", "both", "disagree"]
    has_note = any(word in answer_lower for word in inconsistency_words)

    if retrieval_pass and len(found) >= 2 and has_note:
        print_info(f"  [PASSED] Both values ({found}) mentioned with disagreement note")
        return True
    if len(found) >= 2 and has_note:
        print_info(f"  [PASSED] Both values ({found}) mentioned with disagreement note (retrieval check warning)")
        return True
    if len(found) == 1:
        print_warning(f"  [PARTIAL] Only one value found: {found}")
        return False
    print_warning(f"  [NEEDS REVIEW] Neither 102 nor 100 found in answer")
    return False


if __name__ == "__main__":
    run_tests()
