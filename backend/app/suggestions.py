"""Deterministic follow-up suggestions from the official question bank.

Follows the user's journey:
Eligibility -> Admission -> Fees -> Academic -> Technical -> Student Support -> Career

Rules:
- 3 suggestions after an answered turn: 2 from same category + 1 from next journey step.
- Rewrites with programme context only when answerable for that programme.
- 3 answerable questions about the same programme/topic after not-found answers.
- 4 starter questions after smalltalk.
- None after unrelated queries.
- Never repeats questions already asked in this chat.
- Completely deterministic, zero LLM calls.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.conversation import TurnPlan

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BANK_FILE = os.path.join(DATA_DIR, "question_bank.json")
EVAL_FILE = os.path.join(DATA_DIR, "question_bank_eval.json")

JOURNEY = [
    "Eligibility",
    "Admission",
    "Fees",
    "Academic",
    "Technical",
    "Student Support",
    "Career",
]

CATEGORY_MAP = {
    "Admission Questions": "Admission",
    "Fees Related Questions": "Fees",
    "Academic Questions": "Academic",
    "Technical Questions": "Technical",
    "Career & Placement Questions": "Career",
    "Student Support Questions": "Student Support",
    "General Questions": "Admission",
}

TOPIC_TO_JOURNEY = {
    "eligibility": "Eligibility",
    "admission": "Admission",
    "fees": "Fees",
    "refund": "Fees",
    "subjects": "Academic",
    "subjects/syllabus": "Academic",
    "specializations": "Academic",
    "duration": "Academic",
    "duration/semesters/credits": "Academic",
    "grading": "Academic",
    "exams/grading": "Academic",
    "lms": "Technical",
    "lms/technical": "Technical",
    "contact": "Student Support",
    "support/contact": "Student Support",
    "career": "Career",
    "placement/career": "Career",
    "general": "Admission",
}

STARTER_QUESTIONS = [
    "What online programs are offered?",
    "What is the eligibility for Online MCA?",
    "What is the fee structure for Online BBA?",
    "What is the duration of online programmes?",
]

# Grounded answerable questions from knowledge base audit
DEFAULT_ANSWERABLE_IDS = {
    "Q01", "Q02", "Q04", "Q05", "Q06", "Q07", "Q09", "Q10", "Q11", "Q12",
    "Q13", "Q14", "Q16", "Q17", "Q18", "Q19", "Q20", "Q21", "Q22", "Q23",
    "Q24", "Q26", "Q27", "Q28", "Q29", "Q30", "Q31", "Q32", "Q33", "Q34",
    "Q35", "Q36", "Q37", "Q38", "Q39", "Q40", "Q41", "Q42", "Q43", "Q44",
    "Q45", "Q46", "Q47", "Q48", "Q49", "Q50", "Q51", "Q52", "Q53", "Q54",
    "Q55", "Q56", "Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64",
    "Q65", "Q66", "Q67", "Q68", "Q69", "Q70", "Q71", "Q72", "Q73", "Q74",
    "Q75", "Q76", "Q77",
}

_BANK_CACHE: Optional[List[Dict[str, Any]]] = None
_EVAL_CACHE: Optional[Dict[str, Any]] = None


def _load_bank() -> List[Dict[str, Any]]:
    global _BANK_CACHE
    if _BANK_CACHE is not None:
        return _BANK_CACHE
    if os.path.exists(BANK_FILE):
        try:
            with open(BANK_FILE, "r", encoding="utf-8") as f:
                _BANK_CACHE = json.load(f)
                return _BANK_CACHE
        except Exception:
            pass
    return []


def _load_eval() -> Dict[str, Any]:
    global _EVAL_CACHE
    if _EVAL_CACHE is not None:
        return _EVAL_CACHE
    if os.path.exists(EVAL_FILE):
        try:
            with open(EVAL_FILE, "r", encoding="utf-8") as f:
                _EVAL_CACHE = json.load(f)
                return _EVAL_CACHE
        except Exception:
            pass
    return {}


def is_question_answerable(qid: str, prog: Optional[str] = None) -> bool:
    """Check if question is answerable from docs (generic or programme-specific)."""
    eval_data = _load_eval()
    if eval_data and qid in eval_data:
        entry = eval_data[qid]
        if prog:
            prog_status = entry.get("programmes", {}).get(prog)
            if prog_status is not None:
                return prog_status.get("answerable", False)
        return entry.get("status") == "answerable" or entry.get("generic_answerable", False)
    return qid in DEFAULT_ANSWERABLE_IDS


def _extract_asked_questions(history: Optional[List[Dict[str, Any]]], current_q: str) -> Set[str]:
    """Collect normalized representations of all questions previously asked."""
    asked = set()

    def _normalize(t: str) -> str:
        t = re.sub(r"[^\w\s]", "", t.lower())
        return " ".join(t.split())

    if current_q:
        asked.add(_normalize(current_q))

    for msg in history or []:
        role = msg.get("role") if isinstance(msg, dict) else "user"
        if role == "assistant":
            continue
        content = (msg.get("content") or msg.get("question") or "") if isinstance(msg, dict) else str(msg)
        if content:
            norm = _normalize(content)
            asked.add(norm)
            tokens = norm.split()
            if len(tokens) >= 3:
                asked.add(" ".join(tokens[:3]))

    return asked


def _is_similar(q_text: str, asked_set: Set[str]) -> bool:
    """Fuzzy check whether question has already been asked."""
    norm = re.sub(r"[^\w\s]", "", q_text.lower()).strip()
    norm = " ".join(norm.split())
    if norm in asked_set:
        return True
    tokens = norm.split()
    if len(tokens) >= 3 and " ".join(tokens[:3]) in asked_set:
        return True
    # Word overlap check
    token_set = set(tokens)
    for asked in asked_set:
        asked_tokens = set(asked.split())
        if not asked_tokens:
            continue
        # If the asked query is short and covers the exact same attribute
        if any(t in asked_tokens for t in ["subjects", "subject"]) and "subjects are covered" in norm:
            return True
        if any(t in asked_tokens for t in ["fee", "fees"]) and "first year fee" in norm:
            return True
        if len(asked_tokens) >= 4 and len(token_set & asked_tokens) / max(len(token_set), len(asked_tokens)) > 0.6:
            return True
    return False


def _rewrite_for_programme(text: str, prog_display: str) -> str:
    """Rewrite a generic question to include the programme name naturally."""
    t = text.strip().rstrip("?")
    lowered = t.lower()
    if "for each program" in lowered:
        t = re.sub(r"for each program\b", f"for {prog_display}", t, flags=re.IGNORECASE)
    elif "each program" in lowered:
        t = re.sub(r"each program\b", prog_display, t, flags=re.IGNORECASE)
    elif "this program" in lowered:
        t = re.sub(r"this program\b", prog_display, t, flags=re.IGNORECASE)
    elif "the program" in lowered:
        t = re.sub(r"the program\b", prog_display, t, flags=re.IGNORECASE)
    elif "online programs" in lowered or "online degree programs" in lowered:
        t = re.sub(r"online (?:degree )?programs\b", prog_display, t, flags=re.IGNORECASE)
    else:
        t = f"{t} for {prog_display}"
    return f"{t}?"


def generate_suggestions(
    plan: TurnPlan,
    answer: str,
    history: Optional[List[Dict[str, Any]]] = None,
    is_smalltalk: bool = False,
    is_unrelated: bool = False,
) -> List[str]:
    """Generate up to 3 deterministic, journey-aware suggestions from the question bank."""
    if is_unrelated:
        return []

    bank = _load_bank()
    if not bank:
        return []

    asked_set = _extract_asked_questions(history, plan.standalone_question)

    # 1. Small talk: return starter questions
    if is_smalltalk:
        starters = []
        for sq in STARTER_QUESTIONS:
            if not _is_similar(sq, asked_set):
                starters.append(sq)
        return starters[:4] or STARTER_QUESTIONS[:4]

    # Check for not-found or missing marker
    ans_lower = answer.lower() if answer else ""
    is_not_found = (
        "[[not_found]]" in ans_lower
        or ans_lower.startswith("i couldn't find")
        or "[[missing:" in ans_lower
    )

    prog_display = None
    prog_code = None
    if plan.programmes:
        first_prog = plan.programmes[0]
        prog_code = first_prog
        display_map = {
            "online_bba": "Online BBA",
            "online_bca": "Online BCA",
            "online_mba": "Online MBA",
            "online_mca": "Online MCA",
        }
        prog_display = display_map.get(first_prog)

    # Determine current journey step
    current_step = TOPIC_TO_JOURNEY.get(plan.topic, "Admission")

    # 2. Not-found handling: 3 answerable questions in same topic / programme
    if is_not_found:
        candidates = []
        for item in bank:
            qid = item["id"]
            if not is_question_answerable(qid, prog_code):
                continue
            cat_step = CATEGORY_MAP.get(item["category"], "Admission")
            if cat_step == current_step or any(t in item.get("topics", []) for t in [plan.topic]):
                raw_text = item["text"]
                if prog_display and item.get("programme_specific"):
                    rewritten = _rewrite_for_programme(raw_text, prog_display)
                else:
                    rewritten = raw_text
                if not _is_similar(rewritten, asked_set):
                    candidates.append(rewritten)
                    if len(candidates) == 3:
                        break
        return candidates

    # 3. Answered turn: 2 from same category + 1 from next journey category
    curr_idx = JOURNEY.index(current_step) if current_step in JOURNEY else 0
    next_step = JOURNEY[(curr_idx + 1) % len(JOURNEY)]

    same_pool: List[str] = []
    next_pool: List[str] = []

    for item in bank:
        qid = item["id"]
        if not is_question_answerable(qid, prog_code):
            continue

        cat_step = CATEGORY_MAP.get(item["category"], "Admission")
        raw_text = item["text"]

        if prog_display and item.get("programme_specific"):
            # Rewrite only if answerable for that programme
            if is_question_answerable(qid, prog_code):
                formatted_text = _rewrite_for_programme(raw_text, prog_display)
            else:
                formatted_text = raw_text
        else:
            formatted_text = raw_text

        if _is_similar(formatted_text, asked_set):
            continue

        if cat_step == current_step:
            same_pool.append(formatted_text)
        elif cat_step == next_step:
            next_pool.append(formatted_text)

    suggestions: List[str] = []
    seen = set()

    for q in same_pool:
        if q not in seen:
            seen.add(q)
            suggestions.append(q)
            if len(suggestions) == 2:
                break

    for q in next_pool:
        if q not in seen:
            seen.add(q)
            suggestions.append(q)
            break

    # If same or next pool ran short, backfill from other answerable questions in journey order
    if len(suggestions) < 3:
        for step in JOURNEY:
            for item in bank:
                qid = item["id"]
                if not is_question_answerable(qid, prog_code):
                    continue
                q = item["text"]
                if prog_display and item.get("programme_specific"):
                    q = _rewrite_for_programme(q, prog_display)
                if q not in seen and not _is_similar(q, asked_set):
                    seen.add(q)
                    suggestions.append(q)
                    if len(suggestions) == 3:
                        break
            if len(suggestions) == 3:
                break

    return suggestions[:3]
