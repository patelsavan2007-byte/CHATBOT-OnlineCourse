from __future__ import annotations

from typing import Dict, List, Tuple

from langchain_core.documents import Document

from app import config
from app.conflict import detect_conflicts_from_documents, format_conflict_notice
from app.llm import LLMClient, LLMStatus
from app.prompt import build_prompt, build_prompt_with_history
from app.query_resolver import resolve_followup_query
from app.retriever import RAGRetriever
from app.utils import logger


class RAGChain:
    """Compose retrieval -> conflict detection -> context -> LLM answer."""

    def __init__(self, retriever: RAGRetriever, llm_client: LLMClient) -> None:
        self.retriever = retriever
        self.llm_client = llm_client
        self.last_status: str = LLMStatus.FALLBACK
        self.last_conflicts: List[dict] = []
        self.last_timing: Dict[str, float] = {}

    def answer(self, question: str) -> Tuple[str, List[Tuple[Document, float]]]:
        import time
        t_start = time.time()

        t_ret = time.time()
        retrieved = self.retriever.retrieve(question)
        ret_time = time.time() - t_ret

        program_name = getattr(self.retriever, "last_program", "")
        pool_docs = [doc for doc, _ in getattr(self.retriever, "last_pool", retrieved)]
        conflicts = detect_conflicts_from_documents(pool_docs or [doc for doc, _ in retrieved], question, program_name)
        self.last_conflicts = conflicts

        context = self._build_context(retrieved, conflicts)
        prompt = build_prompt(context=context, question=question)

        evidence = [(doc.page_content, dict(doc.metadata)) for doc, _ in retrieved]
        t_llm = time.time()
        response_text, status = self.llm_client.generate(
            prompt,
            context_chunks=evidence,
            conflicts=conflicts,
        )
        llm_time = time.time() - t_llm

        self.last_status = status
        total_time = time.time() - t_start
        self.last_timing = {
            "retrieval_s": round(ret_time, 3),
            "llm_generation_s": round(llm_time, 3),
            "total_s": round(total_time, 3),
        }
        logger.info("RAG pipeline timing: ret=%.3fs, llm=%.3fs, total=%.3fs, status=%s", ret_time, llm_time, total_time, status)
        return response_text, retrieved


    def answer_with_history(
        self,
        question: str,
        history: List[Dict[str, str]],
    ) -> Tuple[str, List[Tuple[Document, float]], str]:
        """Answer a question using conversation history for context.

        This method wraps the existing RAG pipeline with two additional steps:

        1. **Query resolution** — follow-up questions are reformulated into
           standalone queries so the retriever finds the right documents.
        2. **History-aware prompting** — recent conversation turns are included
           in the LLM prompt so the model can produce contextually coherent
           answers.

        Parameters
        ----------
        question:
            The current user question (may be a follow-up).
        history:
            Recent conversation messages (already trimmed by the caller).

        Returns
        -------
        tuple
            ``(answer_text, retrieved_docs, resolved_query)`` where
            *resolved_query* is the standalone version of the question used
            for retrieval.
        """
        import time
        t_start = time.time()

        # Step 1: Resolve follow-ups into standalone queries
        t_res = time.time()
        resolved_query = resolve_followup_query(
            question, history, llm_client=self.llm_client,
        )
        res_time = time.time() - t_res

        # Step 2: Retrieve using the resolved (standalone) query
        t_ret = time.time()
        retrieved = self.retriever.retrieve(resolved_query)
        ret_time = time.time() - t_ret
        program_name = getattr(self.retriever, "last_program", "")

        pool_docs = [doc for doc, _ in getattr(self.retriever, "last_pool", retrieved)]
        conflicts = detect_conflicts_from_documents(
            pool_docs or [doc for doc, _ in retrieved],
            resolved_query,
            program_name,
        )
        self.last_conflicts = conflicts

        # Step 3: Build context
        context = self._build_context(retrieved, conflicts)

        # Step 4: Build history-aware prompt
        prompt = build_prompt_with_history(
            context=context,
            question=question,
            history=history,
        )

        # Step 5: Generate answer
        evidence = [(doc.page_content, dict(doc.metadata)) for doc, _ in retrieved]
        t_llm = time.time()
        response_text, status = self.llm_client.generate(
            prompt,
            context_chunks=evidence,
            conflicts=conflicts,
        )
        llm_time = time.time() - t_llm

        self.last_status = status
        total_time = time.time() - t_start
        self.last_timing = {
            "query_resolution_s": round(res_time, 3),
            "retrieval_s": round(ret_time, 3),
            "llm_generation_s": round(llm_time, 3),
            "total_s": round(total_time, 3),
        }
        logger.info("RAG pipeline timing (history): res=%.3fs, ret=%.3fs, llm=%.3fs, total=%.3fs, status=%s", res_time, ret_time, llm_time, total_time, status)
        return response_text, retrieved, resolved_query


    def _build_context(
        self,
        retrieved: List[Tuple[Document, float]],
        conflicts: List[dict],
    ) -> str:
        """Build the compact, structured context sent to the LLM.

        Each chunk gets a rich header (source, page, type, programme, score)
        followed by its content trimmed to ``CONTEXT_CHUNK_MAX_CHARS``. The
        total context is bounded by ``CONTEXT_TOTAL_MAX_CHARS`` so long
        knowledge base pages cannot crowd out later, equally relevant chunks.
        """
        parts: List[str] = []
        total = 0

        for doc, score in retrieved:
            meta = doc.metadata
            header_lines = [f"Source: {meta.get('source', 'unknown')}"]
            if meta.get("page") is not None and str(meta.get("page")) != "":
                header_lines.append(f"Page: {meta.get('page')}")
            header_lines.append(f"Chunk ID: {meta.get('chunk_id', 'n/a')}")
            if meta.get("content_type"):
                header_lines.append(f"Content Type: {meta.get('content_type')}")
            if meta.get("document_type"):
                header_lines.append(f"Document Type: {meta.get('document_type')}")
            if meta.get("program_name"):
                header_lines.append(f"Programme: {meta.get('program_name')}")
            header_lines.append(f"Score: {score:.3f}")

            content = doc.page_content.strip()
            if len(content) > config.CONTEXT_CHUNK_MAX_CHARS:
                content = content[: config.CONTEXT_CHUNK_MAX_CHARS] + " ..."

            block = "\n".join(header_lines) + "\nContent:\n" + content
            block_size = len(block) + 4  # account for the "\n\n---\n\n" separator

            if total + block_size > config.CONTEXT_TOTAL_MAX_CHARS:
                remaining = config.CONTEXT_TOTAL_MAX_CHARS - total
                if remaining <= 100:
                    break
                parts.append(block[:remaining])
                total += remaining
                break
            parts.append(block)
            total += block_size

        context = "\n\n---\n\n".join(parts)
        if conflicts:
            context = format_conflict_notice(conflicts) + "\n\n" + context
        return context

