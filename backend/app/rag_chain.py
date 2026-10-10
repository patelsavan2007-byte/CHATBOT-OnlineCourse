from __future__ import annotations

from typing import Dict, List, Tuple

from langchain_core.documents import Document

from app import config
from app.cache import get_cache
from app.conflict import detect_conflicts_from_documents, format_conflict_notice
from app.llm import LLMClient, LLMStatus, NOT_FOUND_ANSWER, build_not_found_answer, strip_internal_references
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

    def answer(
        self,
        question: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, List[Tuple[Document, float]]]:
        import time
        t_start = time.time()

        from app.conversation import analyze_turn
        plan = analyze_turn(question, history=history)

        logger.info("[RAG] Processing query: %r (standalone: %r, programmes: %s)", question, plan.standalone_question, plan.programmes)

        # Check cache first using standalone question and programmes
        if self.cache:
            cached_result = self.cache.get(plan.standalone_question, plan.programmes)
            if cached_result is not None:
                cached_answer, cached_sources = cached_result
                self.last_status = "cached"
                self.last_timing = {
                    "retrieval_s": 0.0,
                    "llm_generation_s": 0.0,
                    "total_s": round(time.time() - t_start, 3),
                }
                logger.info("[RAG] Cache hit, returning cached answer and sources")
                return cached_answer, cached_sources

        # Check for vague query with no programme context
        from app.query_expansion import is_vague_query, vague_clarification_message
        if is_vague_query(question) and not plan.programmes:
            answer = vague_clarification_message()
            self.last_status = "vague_clarification"
            self.last_timing = {
                "retrieval_s": 0.0,
                "total_s": round(time.time() - t_start, 3),
            }
            return answer, []

        t_ret = time.time()
        retrieved = self.retriever.retrieve(question, plan=plan)
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

        context = self._build_context(retrieved, conflicts, plan=plan)
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

        # Cache only answers produced by gemini/groq with retrieved chunks and not NOT_FOUND
        if self.cache and retrieved and any(s in str(status).lower() for s in ("gemini", "groq")):
            is_not_found = any(phrase in answer.lower() for phrase in ("couldn't find", "could not find", "not found", "no information in the official"))
            if not is_not_found:
                self.cache.set(
                    plan.standalone_question,
                    plan.programmes,
                    answer,
                    retrieved,
                    status=status,
                )

        return answer, retrieved


    def _format_chunk(self, doc: Document, score: float) -> str:
        """Format a single document chunk for the context window."""
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

        return "\n".join(header_lines) + "\nContent:\n" + content

    def _build_context(
        self,
        retrieved: List[Tuple[Document, float]],
        conflicts: List[dict],
        plan: Optional[Any] = None,
    ) -> str:
        """Build the compact, structured context sent to the LLM.

        Each chunk gets a rich header (source, page, type, programme, score)
        followed by its content trimmed to ``CONTEXT_CHUNK_MAX_CHARS``.
        When multiple programmes are represented, chunks are grouped under
        programme headers.
        """
        all_progs = ("online_bca", "online_bba", "online_mba", "online_mca")
        distinct_progs = sorted({
            str(doc.metadata.get("program_name", "") or "")
            for doc, _ in retrieved
            if str(doc.metadata.get("program_name", "") or "") in all_progs
        })

        is_multi = len(distinct_progs) >= 2 or (
            plan and (getattr(plan, "is_compare", False) or len(getattr(plan, "programmes", [])) >= 2)
        )

        parts: List[str] = []
        total = 0

        if is_multi:
            prog_labels = {
                "online_bca": "Online BCA (Bachelor of Computer Applications)",
                "online_bba": "Online BBA (Bachelor of Business Administration)",
                "online_mba": "Online MBA (Master of Business Administration)",
                "online_mca": "Online MCA (Master of Computer Applications)",
            }
            grouped: Dict[str, List[Tuple[Document, float]]] = {}
            for doc, score in retrieved:
                pname = str(doc.metadata.get("program_name", "") or "")
                grouped.setdefault(pname, []).append((doc, score))

            for p in distinct_progs:
                if p not in grouped:
                    continue
                header = f"### Programme: {prog_labels.get(p, p.upper())}"
                parts.append(header)
                total += len(header) + 4
                for doc, score in grouped[p]:
                    block = self._format_chunk(doc, score)
                    block_size = len(block) + 4
                    if total + block_size > config.CONTEXT_TOTAL_MAX_CHARS:
                        remaining = config.CONTEXT_TOTAL_MAX_CHARS - total
                        if remaining > 100:
                            parts.append(block[:remaining])
                            total += remaining
                        break
                    parts.append(block)
                    total += block_size

            gen_chunks = [item for pname, items in grouped.items() if pname not in distinct_progs for item in items]
            if gen_chunks and total < config.CONTEXT_TOTAL_MAX_CHARS - 100:
                gen_header = "### General University Information"
                parts.append(gen_header)
                total += len(gen_header) + 4
                for doc, score in gen_chunks:
                    block = self._format_chunk(doc, score)
                    block_size = len(block) + 4
                    if total + block_size > config.CONTEXT_TOTAL_MAX_CHARS:
                        remaining = config.CONTEXT_TOTAL_MAX_CHARS - total
                        if remaining > 100:
                            parts.append(block[:remaining])
                            total += remaining
                        break
                    parts.append(block)
                    total += block_size
        else:
            for doc, score in retrieved:
                block = self._format_chunk(doc, score)
                block_size = len(block) + 4

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


