from __future__ import annotations

from typing import Dict, List, Tuple

from langchain_core.documents import Document

from app import config
from app.conflict import detect_conflicts_from_documents, format_conflict_notice
from app.llm import LLMClient, LLMStatus, NOT_FOUND_ANSWER, build_not_found_answer, strip_internal_references
from app.prompt import build_prompt
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

    @staticmethod
    def _fallback_answer(reason: str) -> Tuple[str, str]:
        """Return the safe not-found answer when no evidence was retrieved."""
        return build_not_found_answer(), reason

    def answer(self, question: str) -> Tuple[str, List[Tuple[Document, float]]]:
        import time
        t_start = time.time()

        logger.info("[RAG] Processing query: %r", question)

        t_ret = time.time()
        retrieved = self.retriever.retrieve(question)
        ret_time = time.time() - t_ret

        logger.info("[RAG] Retrieved relevant chunks: %d", len(retrieved))

        program_name = getattr(self.retriever, "last_program", "")

        if not retrieved:
            answer, status = self._fallback_answer("no_chunks_above_threshold")
            self.last_status = LLMStatus.EMPTY
            self.last_timing = {
                "retrieval_s": round(ret_time, 3),
                "total_s": round(time.time() - t_start, 3),
            }
            return answer, retrieved

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

        answer = strip_internal_references(response_text)
        if not answer:
            answer = build_not_found_answer()
            status = f"{status}|no_content_after_sanitize"
        elif any(phrase in answer.lower() for phrase in ("couldn't find", "could not find", "not found", "no information in the available")):
            answer = build_not_found_answer()
            status = f"{status}|not_found_after_sanitize"

        self.last_status = status
        total_time = time.time() - t_start
        self.last_timing = {
            "retrieval_s": round(ret_time, 3),
            "llm_generation_s": round(llm_time, 3),
            "total_s": round(total_time, 3),
        }
        logger.info("RAG pipeline timing: ret=%.3fs, llm=%.3fs, total=%.3fs, status=%s", ret_time, llm_time, total_time, status)
        return answer, retrieved


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
            context = format_conflict_notice(conflicts, include_locations=False) + "\n\n" + context
        return context

