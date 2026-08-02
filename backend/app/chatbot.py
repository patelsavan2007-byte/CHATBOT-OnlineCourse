from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from langchain_core.documents import Document
from rich.panel import Panel
from rich.prompt import Prompt

from app.config import ensure_directories
from app.embeddings import EmbeddingStore
from app.ingestion import KnowledgeBaseIngester
from app.llm import LLMClient
from app.rag_chain import RAGChain
from app.retriever import RAGRetriever
from app.utils import console, print_info, print_section, print_warning, Timer


class ChatbotApp:
    def __init__(self) -> None:
        ensure_directories()
        self.ingester = KnowledgeBaseIngester()
        self.embedding_store = EmbeddingStore()
        self.vector_store = self._initialize_vector_store()
        self.retriever = RAGRetriever(self.vector_store)
        self.llm_client = LLMClient()
        self.rag_chain = RAGChain(self.retriever, self.llm_client)

    def _initialize_vector_store(self):
        scraped_files = self.ingester.refresh_sources()
        if self.ingester.should_rebuild_vector_store() or scraped_files:
            documents = self.ingester.load_documents()
            chunks = self.ingester.split_documents(documents)
            self.ingester.reset_vector_store()
            vector_store = self.embedding_store.build_vector_store(chunks)
            self.ingester.write_source_manifest()
            self._print_rebuild_summary(scraped_files, documents, chunks)
            return vector_store

        try:
            return self.embedding_store.load_vector_store()
        except Exception:
            documents = self.ingester.load_documents()
            chunks = self.ingester.split_documents(documents)
            self.ingester.reset_vector_store()
            vector_store = self.embedding_store.build_vector_store(chunks)
            self.ingester.write_source_manifest()
            self._print_rebuild_summary(scraped_files, documents, chunks)
            return vector_store

    def _print_rebuild_summary(self, scraped_files: List[Path], documents: List[Document], chunks: List[Document]) -> None:
        pages_crawled = len(scraped_files)
        markdown_files = len(documents)
        chunks_generated = len(chunks)

        print_info("=" * 50)
        print_info(f"Pages Crawled: {pages_crawled}")
        print_info(f"Markdown Files Created: {markdown_files}")
        print_info(f"Chunks Generated: {chunks_generated}")
        print_info(f"Embeddings Generated: {chunks_generated}")
        print_info("ChromaDB Rebuilt Successfully")
        print_info("=" * 50)

    def run(self) -> None:
        print_section("CHARUSAT Online Course Assistant")
        console.print(Panel("Ask questions about the university knowledge base. Type 'exit' to quit."))

        while True:
            try:
                question = Prompt.ask("\nAsk Question")
            except KeyboardInterrupt:
                print_warning("Goodbye!")
                break

            if question.strip().lower() in {"exit", "quit"}:
                print_warning("Goodbye!")
                break

            with Timer() as timer:
                response_text, retrieved = self.rag_chain.answer(question)

            self._display_result(question, response_text, retrieved, timer.elapsed_seconds)

    def _display_result(self, question: str, response_text: str, retrieved: List[Tuple[Document, float]], elapsed_seconds: float) -> None:
        console.print(Panel(f"[bold]Question[/bold]\n{question}", expand=False))

        sources = sorted({doc.metadata.get("source", "unknown") for doc, _ in retrieved})
        chunk_ids = sorted({doc.metadata.get("chunk_id", "n/a") for doc, _ in retrieved})
        scores = [round(score, 4) for _, score in retrieved]

        console.print("[bold]Retrieved Source Files[/bold]")
        for source in sources:
            console.print(f"- {source}")

        console.print("[bold]Retrieved Chunk IDs[/bold]")
        console.print(f"- {', '.join(str(item) for item in chunk_ids)}")

        console.print("[bold]Similarity Scores[/bold]")
        console.print(f"- {', '.join(str(item) for item in scores)}")

        console.print("[bold]Final Answer[/bold]")
        console.print(response_text)

        console.print(f"[bold]Response Time[/bold]: {elapsed_seconds:.2f}s")
        console.print("-" * 50)
