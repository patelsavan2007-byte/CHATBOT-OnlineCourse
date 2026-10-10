"""Evaluate all 77 questions from the question bank through the RAG pipeline.

Determines for each question and programme whether it is:
- answerable: real answer generated, no NOT_FOUND, no [[MISSING]], and at least one supported citation.
- not_in_docs: question cannot be answered from official documents.

Results are saved incrementally in backend/app/data/question_bank_eval.json (resumable).
Kept in repository per Step 8 instructions.
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
import requests

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BACKEND_DIR, "app", "data")
BANK_FILE = os.path.join(DATA_DIR, "question_bank.json")
EVAL_FILE = os.path.join(DATA_DIR, "question_bank_eval.json")
API_URL = "http://127.0.0.1:8000/api/chat"

PROGRAMMES = [
    ("Online BBA", "online_bba"),
    ("Online BCA", "online_bca"),
    ("Online MBA", "online_mba"),
    ("Online MCA", "online_mca"),
]


def load_question_bank() -> List[Dict[str, Any]]:
    if not os.path.exists(BANK_FILE):
        from build_question_bank import build_question_bank
        return build_question_bank()
    with open(BANK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_eval_cache() -> Dict[str, Any]:
    if os.path.exists(EVAL_FILE):
        try:
            with open(EVAL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_eval_cache(data: Dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(EVAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def call_chat_api(question: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Call the live /api/chat endpoint."""
    headers = {"Content-Type": "application/json"}
    payload = {"question": question, "history": history or []}
    try:
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        print(f"API call failed for '{question}': {exc}")
    return {"answer": "", "sources": [], "suggested_questions": []}


def is_answerable(answer: str, sources: List[Dict[str, Any]]) -> bool:
    """Check if the answer represents a valid, grounded answer with supported citations."""
    if not answer or not answer.strip():
        return False
    ans_lower = answer.lower()
    if "[[not_found]]" in ans_lower:
        return False
    if ans_lower.startswith("i couldn't find") or ans_lower.startswith("i could not find"):
        return False
    if "[[missing" in ans_lower:
        return False
    # Must have at least one supported citation
    if not sources or len(sources) == 0:
        return False
    return True


def run_question_bank(force_refresh: bool = False) -> None:
    questions = load_question_bank()
    cache = {} if force_refresh else load_eval_cache()

    print(f"Evaluating {len(questions)} questions through {API_URL}...")
    completed = 0

    for item in questions:
        qid = item["id"]
        text = item["text"]
        cat = item["category"]
        is_prog_spec = item.get("programme_specific", False)

        if qid in cache and not force_refresh:
            completed += 1
            continue

        print(f"[{completed + 1}/{len(questions)}] Testing {qid}: {text}")
        
        # 1. Test generic question
        res = call_chat_api(text)
        time.sleep(0.4) # throttle to preserve LLM token limits

        answer = res.get("answer", "")
        sources = res.get("sources", [])
        answerable_generic = is_answerable(answer, sources)

        entry: Dict[str, Any] = {
            "id": qid,
            "text": text,
            "category": cat,
            "programme_specific": is_prog_spec,
            "generic_answerable": answerable_generic,
            "generic_sources_count": len(sources),
            "programmes": {},
            "status": "answerable" if answerable_generic else "not_in_docs",
        }

        # 2. For programme_specific ones that answered generically, test per programme
        if is_prog_spec and answerable_generic:
            for prog_display, prog_code in PROGRAMMES:
                prog_q = f"{text} for {prog_display}"
                prog_res = call_chat_api(prog_q)
                time.sleep(0.3)
                p_ans = prog_res.get("answer", "")
                p_src = prog_res.get("sources", [])
                entry["programmes"][prog_code] = {
                    "answerable": is_answerable(p_ans, p_src),
                    "sources_count": len(p_src),
                }

        cache[qid] = entry
        save_eval_cache(cache)
        completed += 1

    # Print summary table
    print("\n" + "=" * 90)
    print(f"{'ID':<6} | {'Category':<26} | {'Status':<14} | Question")
    print("=" * 90)

    ans_count = 0
    not_in_docs_count = 0

    for qid in sorted(cache.keys()):
        e = cache[qid]
        st = e.get("status", "not_in_docs")
        if st == "answerable":
            ans_count += 1
        else:
            not_in_docs_count += 1
        q_text = e["text"]
        if len(q_text) > 42:
            q_text = q_text[:39] + "..."
        print(f"{qid:<6} | {e['category']:<26} | {st:<14} | {q_text}")

    print("=" * 90)
    print(f"Total: {len(cache)} | Answerable: {ans_count} | Not in Docs: {not_in_docs_count}\n")


if __name__ == "__main__":
    force = "--refresh" in sys.argv
    run_question_bank(force_refresh=force)
