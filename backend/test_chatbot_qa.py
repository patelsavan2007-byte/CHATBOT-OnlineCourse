"""Quick test script to run sample questions through the RAG chain."""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.embeddings import EmbeddingStore
from app.llm import LLMClient
from app.rag_chain import RAGChain
from app.retriever import RAGRetriever
from app.utils import print_info, print_section, print_warning

questions = [
    "What is the eligibility for Online BCA?",
    "What is the fee for Online BBA?",
    "What is the refund policy?",
    "What are the MBA specializations?",
    "What is the total number of credits in the MBA programme?",
]

print_section("Testing Chatbot Answers Across All PDFs")

store = EmbeddingStore()
vector_store = store.load_vector_store()
retriever = RAGRetriever(vector_store)
llm = LLMClient()
chain = RAGChain(retriever, llm)

for q in questions:
    print_info("=" * 60)
    print_info(f"QUESTION: {q}")
    answer, retrieved = chain.answer(q)

    print_info("RETRIEVED SOURCES:")
    sources = set(f"{doc.metadata.get('source')} (Page {doc.metadata.get('page', 'n/a')})" for doc, _ in retrieved)
    for s in sorted(sources):
        print_info(f"  - {s}")

    print_info(f"LLM STATUS: {chain.last_status}")
    if chain.last_conflicts:
        print_warning(f"CONFLICTS DETECTED: {len(chain.last_conflicts)}")

    print_info("\nANSWER:")
    print_info(answer)
    print_info("")
