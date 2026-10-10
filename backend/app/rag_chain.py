from __future__ import annotations

from typing import Dict, List, Tuple

from langchain_core.documents import Document

from app import config
from app.cache import get_cache
from app.conflict import detect_conflicts_from_documents, format_conflict_notice
from app.llm import LLMClient, LLMStatus, NOT_FOUND_ANSWER, build_not_found_answer, strip_internal_references
from app.multilingual import detect_language
from app.prompt import build_prompt
from app.retriever import RAGRetriever
from app.utils import logger


class RAGChain:
    """Compose retrieval -> conflict detection -> context -> LLM answer."""

    def __init__(self, retriever: RAGRetriever, llm_client: LLMClient, use_cache: bool = True) -> None:
        self.retriever = retriever
        self.llm_client = llm_client
        self.use_cache = use_cache
        self.cache = get_cache() if use_cache else None
        self.last_status: str = LLMStatus.FALLBACK
        self.last_conflicts: List[dict] = []
        self.last_timing: Dict[str, float] = {}

    @staticmethod
    def _fallback_answer(reason: str, question: str = "") -> Tuple[str, str]:
        """Return the safe not-found answer when no evidence was retrieved."""
        return build_not_found_answer(question), reason

    def answer(self, question: str) -> Tuple[str, List[Tuple[Document, float]]]:
        import time
        t_start = time.time()

        logger.info("[RAG] Processing query: %r", question)

        # Check cache first
        if self.cache:
            cached_result = self.cache.get(question)
            if cached_result is not None:
                cached_answer, cached_sources = cached_result
                self.last_status = "cached"
                self.last_timing = {
                    "retrieval_s": 0.0,
                    "llm_generation_s": 0.0,
                    "total_s": round(time.time() - t_start, 3),
                }
                logger.info("[RAG] Cache hit, returning cached answer")
                return cached_answer, []

        # Detect language for multilingual support
        language = detect_language(question)
        logger.info("[RAG] Detected language: %s", language)

        # Fix 6: Check for vague query with no programme context
        from app.query_expansion import is_vague_query, vague_clarification_message, detect_programme_context
        prog_context = detect_programme_context(self.retriever.conversation_history) if self.retriever.conversation_history else None
        if is_vague_query(question) and not prog_context:
            answer = vague_clarification_message()
            self.last_status = "vague_clarification"
            self.last_timing = {
                "retrieval_s": 0.0,
                "total_s": round(time.time() - t_start, 3),
            }
            self.retriever.update_conversation_history(question, answer)
            return answer, []

        t_ret = time.time()
        retrieved = self.retriever.retrieve(question)
        ret_time = time.time() - t_ret

        logger.info("[RAG] Retrieved relevant chunks: %d", len(retrieved))

        program_name = getattr(self.retriever, "last_program", "")

        if not retrieved:
            answer, status = self._fallback_answer("no_chunks_above_threshold", question)
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
        prompt = build_prompt(context=context, question=question, language=language)

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
            answer = build_not_found_answer(question)
            status = f"{status}|no_content_after_sanitize"
        elif any(phrase in answer.lower() for phrase in ("couldn't find", "could not find", "not found", "no information in the available")):
            answer = build_not_found_answer(question)
            status = f"{status}|not_found_after_sanitize"

        self.last_status = status
        total_time = time.time() - t_start
        self.last_timing = {
            "retrieval_s": round(ret_time, 3),
            "llm_generation_s": round(llm_time, 3),
            "total_s": round(total_time, 3),
        }
        logger.info("RAG pipeline timing: ret=%.3fs, llm=%.3fs, total=%.3fs, status=%s", ret_time, llm_time, total_time, status)

        # Cache the result
        if self.cache:
            sources_list = [
                {
                    "source": doc.metadata.get("source", ""),
                    "page": doc.metadata.get("page"),
                    "score": score,
                }
                for doc, score in retrieved
            ]
            self.cache.set(question, answer, sources_list)

        # Update conversation history for query expansion
        self.retriever.update_conversation_history(question, answer)

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
            content_cap = (
                config.CONTEXT_TABLE_MAX_CHARS
                if meta.get("content_type") == "table"
                else config.CONTEXT_CHUNK_MAX_CHARS
            )
            if len(content) > content_cap:
                content = content[:content_cap] + " ..."

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

