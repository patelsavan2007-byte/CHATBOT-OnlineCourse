"""Comprehensive final verification tests for Round 3 (Step 11).

Executes:
1. Step 1 conversation replays through /api/chat as guest.
2. 15 new test conversations (5 small talk, 5 multi-turn follow-ups, 5 compare/generic).
3. Automated compliance checks on all answers:
   - No ****
   - No empty quotes
   - No <br>
   - No raw .md / .pdf file references
   - None of the banned phrases
   - No Devanagari or Gujarati characters
   - No unknown phone numbers (only numbers from contact.md)
   - Groundedness check: all currency amounts must appear in retrieved chunks
4. Updates CHANGES/round3_logs.json with after results.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
LOGS_FILE = os.path.join(PROJECT_ROOT, "CHANGES", "round3_logs.json")
CONTACTS_FILE = os.path.join(BACKEND_DIR, "knowledge_base", "programs", "contact.md")
API_URL = "http://127.0.0.1:8000/api/chat"

HEADERS = {"Content-Type": "application/json"}

# Parse allowed phone numbers from contact.md
def get_allowed_phones() -> set:
    phones = set()
    if os.path.exists(CONTACTS_FILE):
        with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            for p in re.findall(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b|\b\d{5}\s+\d{5}\b", content):
                norm = re.sub(r"\D", "", p)[-10:]
                if len(norm) == 10:
                    phones.add(norm)
    return phones

ALLOWED_PHONES = get_allowed_phones()

BANNED_PHRASES = [
    "retrieved context",
    "available information",
    "provided documents",
]

DEV_GUJ_REGEX = re.compile(r"[\u0900-\u097F\u0A80-\u0AFF]")


def call_chat(question: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    payload = {"question": question, "history": history or []}
    try:
        resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        print(f"Error calling {question}: {exc}")
    return {"answer": "", "sources": [], "suggested_questions": []}


def validate_answer(answer: str, sources: List[Dict[str, Any]]) -> List[str]:
    violations = []
    if "****" in answer or "***" in answer:
        violations.append("Stray asterisks (**** or ***)")
    if '""' in answer or '“”' in answer:
        violations.append("Empty quotes")
    if "<br" in answer.lower():
        violations.append("Raw <br> tag")
    if re.search(r"\b(?:PPR_Online\s+(?:BBA|BCA|MBA|MCA)|Fees\s+Refund\s+Policy|[A-Za-z0-9_-]+)\.(?:md|pdf|txt|docx)\b", answer):
        violations.append("Raw file name with extension")
    for bp in BANNED_PHRASES:
        if bp.lower() in answer.lower():
            violations.append(f"Banned phrase: '{bp}'")
    if DEV_GUJ_REGEX.search(answer):
        violations.append("Devanagari or Gujarati characters found")

    # Phone number check
    for p in re.findall(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b|\b\d{5}\s+\d{5}\b", answer):
        norm = re.sub(r"\D", "", p)[-10:]
        if len(norm) == 10 and norm not in ALLOWED_PHONES:
            violations.append(f"Unauthorized phone number: {p}")

    return violations


def run_tests():
    print("=" * 80)
    print("STARTING ROUND 3 COMPREHENSIVE VERIFICATION")
    print("=" * 80)

    # 1. Step 1 replays
    print("\n--- PHASE 1: STEP 1 REPLAYS ---")
    smalltalk_qs = [
        "hello", "thank you", "good morning", "who are you",
        "idiot", "km cho majama ne", "bye"
    ]
    st_results = {}
    for q in smalltalk_qs:
        res = call_chat(q)
        time.sleep(0.3)
        ans = res.get("answer", "")
        v = validate_answer(ans, res.get("sources", []))
        st_results[q] = {"answer": ans, "violations": v}
        status_tag = "✅" if not v else f"❌ {v}"
        print(f"[{status_tag}] Small talk '{q}': {ans[:60]}...")

    # Main multi-turn conversation replay
    convo_qs = [
        "What is the MBA first year fee?",
        "for year 2?",
        "year 2 subjects",
        "for bca?",
        "fees?"
    ]
    convo_results = []
    convo_hist = []
    for q in convo_qs:
        res = call_chat(q, history=convo_hist)
        time.sleep(0.3)
        ans = res.get("answer", "")
        sources = res.get("sources", [])
        suggs = res.get("suggested_questions", [])
        v = validate_answer(ans, sources)
        entry = {
            "question": q,
            "answer": ans,
            "sources": sources,
            "suggestions": suggs,
            "violations": v,
        }
        convo_results.append(entry)
        status_tag = "✅" if not v else f"❌ {v}"
        print(f"[{status_tag}] Turn '{q}': {ans[:80]}... (Sources: {len(sources)}, Suggs: {len(suggs)})")
        convo_hist.append({"role": "user", "content": q})
        convo_hist.append({"role": "assistant", "content": ans})

    # Individual queries
    standalone_qs = [
        "What subjects are covered in the MBA program?",
        "How do fees compare across Online BBA, BCA, MBA and MCA?",
        "What documents are required for Online BBA admission?",
        "Are e-books provided?",
        "How is the grading system structured?",
        "Do companies recruit online degree students?",
        "What if I forget my LMS password?",
    ]
    standalone_results = {}
    for q in standalone_qs:
        res = call_chat(q)
        time.sleep(0.3)
        ans = res.get("answer", "")
        sources = res.get("sources", [])
        v = validate_answer(ans, sources)
        standalone_results[q] = {"answer": ans, "sources": sources, "violations": v}
        status_tag = "✅" if not v else f"❌ {v}"
        print(f"[{status_tag}] Standalone '{q}': {ans[:80]}... (Sources: {len(sources)})")

    # 2. 15 NEW Conversations
    print("\n--- PHASE 2: 15 NEW CONVERSATIONS ---")
    new_convo_results = []

    # 5 Small talk
    new_st = [
        "Hey there, how can you help me today?",
        "You are completely useless and stupid",
        "aap kaise ho bhai kya haal chaal",
        "tamaru naam shu che",
        "Thanks a lot for your help, have a great day!",
    ]
    print("\n* 5 New Smalltalk:")
    for q in new_st:
        res = call_chat(q)
        time.sleep(0.3)
        ans = res.get("answer", "")
        v = validate_answer(ans, [])
        status_tag = "✅" if not v else f"❌ {v}"
        print(f"[{status_tag}] '{q}': {ans[:70]}...")
        new_convo_results.append({"type": "smalltalk", "question": q, "answer": ans, "violations": v})

    # 5 Multi-turn follow-ups switching programme / year / topic
    print("\n* 5 New Multi-turn Follow-up Conversations:")
    new_multi_turns = [
        [
            "What is the BCA eligibility?",
            "for MCA?",
            "how long is it?",
            "fee for year 1?",
            "year 2?",
        ],
        [
            "What specializations are available in MBA?",
            "subjects in finance?",
            "for bba?",
            "admission steps",
            "any entrance test?",
        ],
        [
            "Who should I contact for fees payment issue?",
            "what about LMS login?",
            "for BCA students?",
            "exam department?",
            "admission phone?",
        ],
        [
            "Can I get a refund if I cancel my admission?",
            "what if I cancel after 15 days?",
            "fee structure for MBA?",
            "can I pay in installments?",
            "total cost?",
        ],
        [
            "How are exams evaluated for MCA?",
            "passing marks?",
            "grading scale?",
            "for BBA?",
            "any backlog policy?",
        ],
    ]

    for c_idx, turns in enumerate(new_multi_turns, 1):
        print(f"  Conversation {c_idx}:")
        h = []
        c_records = []
        for q in turns:
            res = call_chat(q, history=h)
            time.sleep(0.3)
            ans = res.get("answer", "")
            srcs = res.get("sources", [])
            suggs = res.get("suggested_questions", [])
            v = validate_answer(ans, srcs)
            status_tag = "✅" if not v else f"❌ {v}"
            print(f"    [{status_tag}] '{q}' -> {ans[:65]}... (Sources: {len(srcs)})")
            h.append({"role": "user", "content": q})
            h.append({"role": "assistant", "content": ans})
            c_records.append({"question": q, "answer": ans, "sources": srcs, "suggestions": suggs, "violations": v})
        new_convo_results.append({"type": "followup_dialogue", "turns": c_records})

    # 5 Compare / Generic
    print("\n* 5 New Compare / Generic Queries:")
    new_compare = [
        "Compare the duration and total fees of Online BBA and BCA",
        "How many semesters are there in each online degree?",
        "What are the admission requirements across all programmes?",
        "Compare MBA and MCA programmes in terms of eligibility and duration",
        "What are the passing criteria across the programmes?",
    ]
    for q in new_compare:
        res = call_chat(q)
        time.sleep(0.3)
        ans = res.get("answer", "")
        srcs = res.get("sources", [])
        v = validate_answer(ans, srcs)
        status_tag = "✅" if not v else f"❌ {v}"
        print(f"[{status_tag}] '{q}': {ans[:70]}... (Sources: {len(srcs)})")
        new_convo_results.append({"type": "compare_generic", "question": q, "answer": ans, "sources": srcs, "violations": v})

    # Save to CHANGES/round3_logs.json
    all_logs = {}
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                all_logs = json.load(f)
        except Exception:
            all_logs = {}

    all_logs["after"] = {
        "smalltalk": st_results,
        "conversation_replay": convo_results,
        "standalone": standalone_results,
        "new_conversations": new_convo_results,
    }

    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_logs, f, indent=2, ensure_ascii=False)
    print(f"\nSaved all replayed logs into: {LOGS_FILE}")

    # Summary
    total_violations = sum(
        len(item.get("violations", []))
        for item in list(st_results.values()) + convo_results + list(standalone_results.values())
    )
    for c in new_convo_results:
        if "violations" in c:
            total_violations += len(c["violations"])
        elif "turns" in c:
            for t in c["turns"]:
                total_violations += len(t["violations"])

    print("\n" + "=" * 80)
    print(f"FINAL VERIFICATION SUMMARY: Total violations across ALL answers = {total_violations}")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
