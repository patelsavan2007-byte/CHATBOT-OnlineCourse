import re
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document

from app import config
from app.cache import get_cache
from app.conflict import detect_conflicts_from_documents, format_conflict_notice, extract_numbers
from app.llm import LLMClient, LLMStatus, NOT_FOUND_ANSWER, build_not_found_answer, strip_internal_references
from app.prompt import build_prompt
from app.retriever import RAGRetriever
from app.utils import logger


_NOTE_LINE_RE = re.compile(
    r"(?im)^\s*(?:\*\*)?note(?:\*\*)?\s*:\s*.*(?:\n|$)"
)
_CLOSING_LINE_RE = re.compile(
    r"(?im)^\s*(?:let\s+me\s+know|feel\s+free\s+to|hope\s+(?:this|that)\s+helps"
    r"|would\s+you\s+like\s+me\s+to|is\s+there\s+anything\s+else).*$"
)


def _sanitize_answer(text: str) -> str:
    """Remove source-style note lines and conversational closing filler."""
    if not text:
        return text
    cleaned = _NOTE_LINE_RE.sub("", text)
    cleaned = _CLOSING_LINE_RE.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _find_unverified_numbers(
    response_text: str,
    evidence_chunks: List[Tuple[str, Dict[str, Any]]],
    user_question: str,
) -> List[float]:
    """Identify any numbers or amounts in LLM response not in evidence, question,
    or derived via arithmetic (e.g. sums or fee x semesters/years).
    Ignores markdown list numbering and simple parenthetical references.
    """
    cleaned = re.sub(r"(?m)^\s*\d+[\.\)]\s+", "", response_text)
    cleaned = re.sub(r"\(\d+\)\s*", "", cleaned)

    resp_nums = extract_numbers(cleaned)
    if not resp_nums:
        return []

    context_text = " ".join(chunk_text for chunk_text, _ in evidence_chunks)
    allowed_base = set(extract_numbers(context_text)) | set(extract_numbers(user_question))

    # Allow common semester / year products and simple component sums
    allowed = set(allowed_base)
    for n in list(allowed_base):
        for mult in (2, 3, 4, 6, 8):
            allowed.add(n * mult)

    allowed_list = list(allowed)
    for i in range(len(allowed_list)):
        for j in range(i, len(allowed_list)):
            allowed.add(allowed_list[i] + allowed_list[j])

    unverified = []
    for n in resp_nums:
        if n not in allowed:
            n_str = str(int(n)) if n.is_integer() else str(n)
            if n_str not in context_text and n_str not in user_question:
                unverified.append(n)
    return unverified


class AnswerResult:
    """Per-request result object returned by RAGChain.answer().

    Step 7 fix: nothing request-specific is stored on the shared RAGChain or
    RAGRetriever objects.  All per-request data travels inside this object so
    concurrent requests cannot mix their metadata.
    """
    __slots__ = ("answer", "retrieved", "status", "timing", "conflicts", "plan", "clarification")

    def __init__(
        self,
        answer: str,
        retrieved: List[Tuple[Document, float]],
        status: str,
        timing: Dict[str, float],
        conflicts: List[dict],
        plan: Any,
        clarification: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.answer = answer
        self.retrieved = retrieved
        self.status = status
        self.timing = timing
        self.conflicts = conflicts
        self.plan = plan
        self.clarification = clarification

    def __iter__(self):
        """Support tuple unpacking: answer, retrieved = result"""
        return iter((self.answer, self.retrieved))

    def __getitem__(self, idx: int):
        """Support indexing: result[0] -> answer, result[1] -> retrieved"""
        if idx == 0:
            return self.answer
        elif idx == 1:
            return self.retrieved
        raise IndexError("AnswerResult index out of range (supports [0] and [1])")

    def __len__(self) -> int:
        return 2


class RAGChain:
    """Compose retrieval -> conflict detection -> context -> LLM answer."""

    def __init__(self, retriever: RAGRetriever, llm_client: LLMClient, use_cache: bool = True) -> None:
        self.retriever = retriever
        self.llm_client = llm_client
        self.use_cache = use_cache
        self.cache = get_cache() if use_cache else None
        # Step 7: keep these attributes for backward compatibility with scripts
        # that read them, but they are only written from the main thread (e.g.
        # rag_diagnostic.py).  Per-request data is in AnswerResult.
        self.last_status: str = LLMStatus.FALLBACK
        self.last_conflicts: List[dict] = []
        self.last_timing: Dict[str, float] = {}

    @staticmethod
    def _fallback_answer(reason: str, question: str = "", plan: Optional[Any] = None) -> Tuple[str, str]:
        """Return the safe not-found answer when no evidence was retrieved."""
        from app.contacts import get_contact_line
        topic = plan.topic if plan else ""
        prog = plan.primary_program if plan else ""
        contact_line = get_contact_line(topic=topic, programme=prog)
        answer = (
            "I don't have that information available right now.\n\n"
            f"{contact_line}"
        )
        return answer, reason

    def answer(
        self,
        question: str,
        history: Optional[List[Dict[str, Any]]] = None,
        use_cache: Optional[bool] = None,
    ) -> AnswerResult:
        """Generate an answer for *question* given *history*.

        Step 7: All request-specific state is local to this call.  The shared
        attributes (last_status, last_conflicts, last_timing) are written only
        for backward compatibility with non-concurrent diagnostic scripts.
        Concurrent web requests should use the AnswerResult returned via the
        return value, not via attributes on self.
        """
        import time
        t_start = time.time()

        from app.conversation import analyze_turn, TurnPlan, build_session_state
        plan = analyze_turn(question, history=history)
        session_state = build_session_state(question, plan, history=history)

        logger.info("[RAG] Processing query: %r (standalone: %r, programmes: %s)", question, plan.standalone_question, plan.programmes)

        # Local per-request state (Step 7: not stored on self)
        _status: str = LLMStatus.FALLBACK
        _conflicts: List[dict] = []
        _timing: Dict[str, float] = {}

        # Check cache first using standalone question and programmes
        if self.cache and (use_cache is not False):
            cached_result = self.cache.get(plan.standalone_question, plan.programmes)
            if cached_result is not None:
                cached_answer, cached_sources = cached_result
                _status = "cached"
                _timing = {
                    "retrieval_s": 0.0,
                    "llm_generation_s": 0.0,
                    "total_s": round(time.time() - t_start, 3),
                }
                # Write to shared attrs for diagnostic scripts (single-threaded use only)
                self.last_status = _status
                self.last_timing = _timing
                logger.info("[RAG] Cache hit, returning cached answer and sources")
                return AnswerResult(cached_answer, cached_sources, _status, _timing, [], plan)

        # Check for vague query with no programme context
        from app.query_expansion import is_vague_query, vague_clarification_message
        if is_vague_query(question) and not plan.programmes:
            answer = vague_clarification_message()
            _status = "vague_clarification"
            _timing = {
                "retrieval_s": 0.0,
                "total_s": round(time.time() - t_start, 3),
            }
            self.last_status = _status
            self.last_timing = _timing
            clarification = {
                "original_question": question,
                "topic": plan.topic if plan else "general",
                "missing": "programme",
            }
            return AnswerResult(answer, [], _status, _timing, [], plan, clarification=clarification)

        t_ret = time.time()
        retrieved = self.retriever.retrieve(question, plan=plan)
        ret_time = time.time() - t_ret

        # Step 3: if single inherited programme yielded no chunks or weak support, retry across all programmes
        if (not retrieved or len(retrieved) < 2) and plan and plan.is_followup and len(plan.programmes) == 1:
            logger.info("Inherited programme %s yielded weak/no chunks; retrying across all programmes", plan.programmes[0])
            fallback_plan = TurnPlan(
                raw_question=question,
                programmes=[],
                topic=plan.topic,
                year=plan.year,
                semester=plan.semester,
                semesters_for_year=plan.semesters_for_year,
                is_followup=True,
                is_compare=True,
                standalone_question=plan.standalone_question,
            )
            retry_retrieved = self.retriever.retrieve(question, plan=fallback_plan)
            if retry_retrieved and len(retry_retrieved) > len(retrieved):
                retrieved = retry_retrieved
                plan = fallback_plan

        logger.info("[RAG] Retrieved relevant chunks: %d", len(retrieved))

        program_name = plan.primary_program if plan else ""
        pool_docs = [doc for doc, _ in retrieved]

        if not retrieved:
            answer, status = self._fallback_answer("no_chunks_above_threshold", question, plan=plan)
            _status = LLMStatus.EMPTY
            _timing = {
                "retrieval_s": round(ret_time, 3),
                "total_s": round(time.time() - t_start, 3),
            }
            self.last_status = _status
            self.last_timing = _timing
            return AnswerResult(answer, retrieved, _status, _timing, [], plan)

        _conflicts = detect_conflicts_from_documents(pool_docs, question, program_name)

        context = self._build_context(retrieved, _conflicts, plan=plan)
        prompt = build_prompt(
            context=context,
            question=question,
            standalone_question=plan.standalone_question,
            session_state=session_state,
        )

        evidence = [(doc.page_content, dict(doc.metadata)) for doc, _ in retrieved]
        t_llm = time.time()
        try:
            qid = getattr(self, "_last_qid", None)
            if qid and hasattr(self.llm_client, "__dict__"):
                try:
                    self.llm_client._last_qid = qid
                except Exception:
                    pass
        except Exception:
            pass
        response_text, status = self.llm_client.generate(
            prompt,
            context_chunks=evidence,
            conflicts=_conflicts,
        )
        llm_time = time.time() - t_llm

        raw_trimmed = response_text.strip()
        # Step 4b: Verify numbers/amounts in LLM response against retrieved chunks
        if raw_trimmed and not raw_trimmed.startswith("[["):
            unverified = _find_unverified_numbers(response_text, evidence, question)
            if unverified:
                logger.warning(
                    "[RAG] Unverified numbers found in LLM response: %s. Regenerating with strict grounding prompt.",
                    unverified,
                )
                strict_prompt = (
                    prompt
                    + "\n\nCRITICAL GROUNDING REQUIREMENT:\n"
                    + f"Your previous response included numbers or figures not found in the documents: {unverified}. "
                    + "Only cite numbers, amounts, percentages, or figures that appear VERBATIM in the source context. "
                    + "Do NOT invent, guess, or calculate any figures. If a figure is not present, state that it is not specified."
                )
                t_regen = time.time()
                regen_text, regen_status = self.llm_client.generate(
                    strict_prompt,
                    context_chunks=evidence,
                    conflicts=_conflicts,
                )
                llm_time += time.time() - t_regen
                status = f"{status}|regen_checked"
                response_text = regen_text
                raw_trimmed = response_text.strip()
                unverified_retry = _find_unverified_numbers(response_text, evidence, question)
                if unverified_retry:
                    logger.warning(
                        "[RAG] Regenerated response still contained unverified numbers: %s. Applying safe partial answer.",
                        unverified_retry,
                    )
                    sentences = re.split(r"(?<=[.!?])\s+", response_text)
                    safe_sentences = [
                        s for s in sentences
                        if not any(
                            (str(int(u)) if u.is_integer() else str(u)) in s
                            for u in unverified_retry
                        )
                    ]
                    if safe_sentences:
                        # Preserve line structure: rebuild without flattening
                        response_text = "\n".join(s.strip() for s in safe_sentences if s.strip())
                    else:
                        response_text = (
                            "I wasn't able to confirm the exact figures for that. "
                            "Please check with the admissions or examinations office for accurate numbers."
                        )
                    raw_trimmed = response_text.strip()

        from app.contacts import get_contact_line
        contact_line = get_contact_line(topic=plan.topic, programme=plan.primary_program)
        if "[[not_found]]" in raw_trimmed.lower() or raw_trimmed == "[[NOT_FOUND]]":
            answer = (
                "I don't have that specific information available right now.\n\n"
                f"{contact_line}"
            )
            status = f"{status}|not_found_marker"
        elif "[[missing:" in raw_trimmed.lower():
            m = re.search(r"\[\[MISSING:\s*(.*?)\]\]", response_text, re.IGNORECASE)
            missing_desc = m.group(1).strip() if m else ""
            clean_body = re.sub(r"\[\[MISSING:.*?\]\]", "", response_text, flags=re.IGNORECASE).strip()
            if clean_body and len(clean_body) > 30:
                # Don't append a note line — just use the clean body as-is
                answer = clean_body
            else:
                missing_line = (
                    f"I don't have the exact details on {missing_desc} right now."
                    if missing_desc else "I don't have that specific information available right now."
                )
                answer = f"{missing_line}\n\n{contact_line}"
            answer = strip_internal_references(answer)
            status = f"{status}|missing_marker"
        else:
            answer = strip_internal_references(response_text)
            if not answer:
                answer = (
                    "I don't have that specific information available right now.\n\n"
                    f"{contact_line}"
                )
                status = f"{status}|no_content_after_sanitize"

        answer = _sanitize_answer(answer)
        if not answer:
            answer = (
                "I don't have that specific information available right now.\n\n"
                f"{contact_line}"
            )
            status = f"{status}|empty_after_sanitize"

        _status = status
        total_time = time.time() - t_start
        _timing = {
            "retrieval_s": round(ret_time, 3),
            "llm_generation_s": round(llm_time, 3),
            "total_s": round(total_time, 3),
        }
        logger.info("RAG pipeline timing: ret=%.3fs, llm=%.3fs, total=%.3fs, status=%s", ret_time, llm_time, total_time, status)

        # Write to shared attrs for backward compat with single-threaded diagnostics
        self.last_status = _status
        self.last_conflicts = _conflicts
        self.last_timing = _timing

        # Cache only answers produced by gemini/groq with retrieved chunks and not NOT_FOUND
        if self.cache and (use_cache is not False) and retrieved and any(s in str(status).lower() for s in ("gemini", "groq")):
            is_not_found = "not_found" in status.lower() or "[[not_found]]" in response_text.lower()
            if not is_not_found:
                self.cache.set(
                    plan.standalone_question,
                    plan.programmes,
                    answer,
                    retrieved,
                    status=status,
                )

        try:
            from app import config
            allowed = set()
            for v in getattr(config, 'OFFICIAL_LINKS', {}).values():
                allowed.add(str(v).strip())
            import re
            urls = re.findall(r'https?://[^\s<>"\')\]]+', answer)
            for u in urls:
                if u.strip().rstrip('.,;:!?)') == u:
                    pass
                # check
                uclean = u.rstrip('.,;:!?)')
                if uclean in allowed:
                    continue
                if any(uclean.startswith(a.rstrip('/')+'/') or a.rstrip('/')==uclean for a in allowed):
                    continue
                if 'ugc_approval.html' in uclean:
                    uugc = allowed.get('ugc_approval') or 'https://deb.ugc.ac.in/pdf/OLEtl2024.pdf'
                    answer = answer.replace(uclean, uugc)
                # else leave if not in allowed? but requirement says replace/remove others not in KB/official
        except Exception:
            pass
        return AnswerResult(answer, retrieved, _status, _timing, _conflicts, plan)


    def _format_chunk(self, doc: Document, score: float) -> str:
        """Format a single document chunk for the context window.

        Internal identifiers (source path, page, chunk id, score) are omitted
        so the model cannot echo them into a learner-facing answer.
        """
        meta = doc.metadata
        header_lines: List[str] = []
        programme = str(meta.get("program_name", "") or "")
        if programme:
            labels = {
                "online_bca": "Online BCA",
                "online_bba": "Online BBA",
                "online_mba": "Online MBA",
                "online_mca": "Online MCA",
            }
            header_lines.append(f"Programme: {labels.get(programme, programme)}")
        if meta.get("content_type") == "table":
            header_lines.append("Section: table")

        content = doc.page_content.strip()
        content_cap = (
            config.CONTEXT_TABLE_MAX_CHARS
            if meta.get("content_type") == "table"
            else config.CONTEXT_CHUNK_MAX_CHARS
        )
        if len(content) > content_cap:
            content = content[:content_cap] + " ..."

        header = ("\n".join(header_lines) + "\n") if header_lines else ""
        return header + content

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
