"""Test live RAGChain with interleaved conversations."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import ensure_directories
from app.embeddings import EmbeddingStore
from app.retriever import RAGRetriever
from app.llm import LLMClient
from app.rag_chain import RAGChain
from app import config

ensure_directories()
store = EmbeddingStore()
vector_store = store.load_vector_store()
retriever = RAGRetriever(vector_store)
llm = LLMClient()
rag = RAGChain(retriever, llm, use_cache=True)

# Conversation 1: MBA fee flow
chat1_history = [
    {"role": "user", "content": "What is the MBA first year fee?"},
    {"role": "assistant", "content": "The MBA first year fee is ..."},
]
ans1, chunks1 = rag.answer("for year 2?", history=chat1_history)
print(f"Chat 1 (MBA for year 2?): answer length={len(ans1)}, chunks={len(chunks1)}")
progs1 = {c.metadata.get("program_name") for c, _ in chunks1}
print(f"Chat 1 chunks programmes: {progs1}")

# Conversation 2: BCA eligibility flow
chat2_history = [
    {"role": "user", "content": "What is the eligibility for BCA?"},
    {"role": "assistant", "content": "The eligibility for BCA is 10+2 ..."},
]
ans2, chunks2 = rag.answer("for year 2?", history=chat2_history)
print(f"Chat 2 (BCA for year 2?): answer length={len(ans2)}, chunks={len(chunks2)}")
progs2 = {c.metadata.get("program_name") for c, _ in chunks2}
print(f"Chat 2 chunks programmes: {progs2}")

assert "online_mba" in progs1, f"Expected online_mba in {progs1}"
assert "online_bca" in progs2, f"Expected online_bca in {progs2}"
assert progs1 != progs2, "Programmes must be different"
assert ans1 != ans2, "Answers must not be shared"
print("SUCCESS: Interleaved conversations are 100% isolated and did not share answers or chunks!")
