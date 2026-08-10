"""Resolve follow-up questions using conversation history.

When a user asks "What about the duration?" after discussing Online MBA fees,
this module reformulates the question into a standalone query like
"What is the duration of Online MBA?" so the RAG retriever can find the right
documents.

The resolution logic is intentionally lightweight:

1. A quick heuristic checks whether the question *needs* resolution (contains
   anaphoric references, lacks a programme name that appears in recent history,
   or is very short).
2. If resolution is needed, the LLM is asked to rewrite the question as a
   standalone query.  This uses a tiny, focused prompt — not the full RAG
   system prompt.
3. If the LLM is unavailable or the heuristic decides the question is already
   self-contained, the original question is returned unchanged.

This module does **not** touch ChromaDB, the vector store, or the retrieval
pipeline.  It sits between the user input and the retriever.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.utils import logger

# Anaphoric / referential cues that suggest the question depends on prior
# context.  Checked case-insensitively.
_FOLLOWUP_CUES = [
    r"\bit\b",
    r"\bits\b",
    r"\bthat\b",
    r"\bthis\b",
    r"\bthe same\b",
    r"\babove\b",
    r"\bprevious\b",
    r"\bsame programme\b",
    r"\bsame program\b",
    r"\bsame course\b",
    r"\bwhat about\b",
    r"\bhow about\b",
    r"\band the\b",
    r"\balso\b",
    r"\btoo\b",
    r"\bas well\b",
]
_FOLLOWUP_RE = re.compile("|".join(_FOLLOWUP_CUES), re.IGNORECASE)

# Programme names we look for to decide if the query is self-contained.
_PROGRAMME_RE = re.compile(
    r"\b(?:online\s+)?(?:bca|bba|mba|mca)\b", re.IGNORECASE
)

_RESOLVE_PROMPT_TEMPLATE = """\
You are a query rewriter for a university chatbot.

Given the recent conversation history and a new follow-up question, rewrite \
the follow-up question as a **standalone, self-contained question** that \
includes all necessary context (programme name, attribute, etc.) so it can be \
understood without the conversation history.

Rules:
- Output ONLY the rewritten question, nothing else.
- Do NOT answer the question.
- If the question is already self-contained, return it unchanged.
- Keep the rewritten question concise and natural.

Conversation History:
{history}

Follow-up Question:
{question}

Rewritten Question:"""


def needs_resolution(question: str, history: List[Dict[str, str]]) -> bool:
    """Return ``True`` if *question* likely needs context from *history*.

    The heuristic is deliberately conservative: it flags questions that
    contain referential words or that lack a programme name while the
    history mentions one.
    """
    if not history:
        return False

    # Very short questions are often follow-ups ("And the fee?", "Duration?")
    if len(question.split()) <= 3:
        return True

    # Contains anaphoric cues
    if _FOLLOWUP_RE.search(question):
        return True

    # History mentions a programme but the current question does not
    if not _PROGRAMME_RE.search(question):
        history_text = " ".join(m["content"] for m in history)
        if _PROGRAMME_RE.search(history_text):
            return True

    return False


def _format_history_for_prompt(history: List[Dict[str, str]]) -> str:
    """Format recent history as ``User: … / Assistant: …`` pairs."""
    lines = []
    for msg in history:
        role_label = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role_label}: {msg['content']}")
    return "\n".join(lines)


def resolve_followup_query(
    question: str,
    history: List[Dict[str, str]],
    *,
    llm_client: Optional[object] = None,
) -> str:
    """Rewrite *question* into a standalone query using *history*.

    Parameters
    ----------
    question:
        The raw user question (may be a follow-up).
    history:
        Recent conversation messages (``[{"role": ..., "content": ...}, ...]``).
    llm_client:
        An ``LLMClient`` instance.  If ``None`` or the LLM call fails, a
        simple heuristic fallback is attempted (programme-name injection).

    Returns
    -------
    str
        Either the reformulated standalone question or the original question
        if resolution was not needed or failed.
    """
    if not needs_resolution(question, history):
        logger.info("Query resolution: question is self-contained, no rewrite needed")
        return question

    logger.info("Query resolution: follow-up detected, attempting rewrite")

    # ---- Try LLM-based resolution ----
    if llm_client is not None:
        try:
            history_text = _format_history_for_prompt(history[-6:])  # last 3 pairs max
            prompt = _RESOLVE_PROMPT_TEMPLATE.format(
                history=history_text,
                question=question,
            )
            resolved, _status = llm_client.generate(prompt)
            resolved = resolved.strip().strip('"').strip("'").strip()
            if resolved and len(resolved) < 500:
                logger.info("Query resolved via LLM: %r -> %r", question, resolved)
                return resolved
        except Exception as exc:
            logger.warning("LLM query resolution failed: %s", exc)

    # ---- Heuristic fallback: inject programme name from history ----
    resolved = _heuristic_resolve(question, history)
    if resolved != question:
        logger.info("Query resolved via heuristic: %r -> %r", question, resolved)
    else:
        logger.info("Query resolution: no rewrite applied, using original")
    return resolved


def _heuristic_resolve(
    question: str,
    history: List[Dict[str, str]],
) -> str:
    """Best-effort heuristic: prepend the programme name from history."""
    if _PROGRAMME_RE.search(question):
        return question

    # Find the most recent programme mention in history (scan backwards)
    for msg in reversed(history):
        match = _PROGRAMME_RE.search(msg["content"])
        if match:
            programme = match.group(0)
            # Prepend context: "What about the fee?" -> "Regarding Online MBA, What about the fee?"
            return f"Regarding {programme}, {question}"

    return question
