#!/usr/bin/env python3
"""Smoke tests for the CHARUSAT Online Course Chatbot.

Verifies that backend API endpoints are healthy and the optional frontend
is reachable.  Uses only the ``requests`` library (no heavy ML deps).

Usage
-----
    python smoke_test.py --backend http://localhost:8000
    python smoke_test.py --backend http://localhost:8000 --frontend https://your-app.vercel.app

Exit code 0 = all tests passed, 1 = at least one failure.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Optional


try:
    import requests
except ImportError:
    print("ERROR: 'requests' library is required.  Install with:  pip install requests")
    sys.exit(1)

# Force UTF-8 output on Windows (avoids cp1252 encoding errors)
import io, os
if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")



# ── Colours (ANSI) ───────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

passed = 0
failed = 0


def ok(name: str, detail: str = ""):
    global passed
    passed += 1
    print(f"  {GREEN}✔ PASS{RESET}  {name}  {CYAN}{detail}{RESET}")


def fail(name: str, detail: str = ""):
    global failed
    failed += 1
    print(f"  {RED}✘ FAIL{RESET}  {name}  {YELLOW}{detail}{RESET}")


# ── Test functions ───────────────────────────────────────────────
def test_health(base: str) -> bool:
    """GET /health — must return 200 with vector_store_documents > 0."""
    url = f"{base}/health"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        if r.status_code == 200 and data.get("status") == "ok":
            docs = data.get("vector_store_documents", 0)
            if docs > 0:
                ok("Health check", f"status=ok  docs={docs}")
                return True
            else:
                fail("Health check", f"vector store empty (docs={docs})")
                return False
        else:
            fail("Health check", f"status_code={r.status_code} body={r.text[:200]}")
            return False
    except Exception as exc:
        fail("Health check", str(exc))
        return False


def test_root(base: str) -> bool:
    """GET / — should return 200 (root welcome endpoint)."""
    url = f"{base}/"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            ok("Root endpoint", "GET / → 200")
            return True
        else:
            fail("Root endpoint", f"GET / → {r.status_code}")
            return False
    except Exception as exc:
        fail("Root endpoint", str(exc))
        return False


def test_chat(base: str) -> Optional[str]:
    """POST /chat — send a test question and validate response shape."""
    url = f"{base}/chat"
    payload = {"question": "What online programmes does CHARUSAT offer?"}
    try:
        r = requests.post(url, json=payload, timeout=120)
        if r.status_code != 200:
            fail("Chat endpoint", f"status={r.status_code} body={r.text[:300]}")
            return None
        data = r.json()
        session_id = data.get("session_id")
        answer = data.get("answer", "")
        sources = data.get("sources", [])
        llm_status = data.get("llm_status", "")

        missing = []
        if not session_id:
            missing.append("session_id")
        if not answer:
            missing.append("answer")

        if missing:
            fail("Chat endpoint", f"missing fields: {missing}")
            return None

        ok(
            "Chat endpoint",
            f"session={session_id[:8]}…  answer_len={len(answer)}  "
            f"sources={len(sources)}  llm={llm_status}",
        )
        return session_id
    except Exception as exc:
        fail("Chat endpoint", str(exc))
        return None


def test_followup(base: str, session_id: str) -> bool:
    """POST /chat with existing session — tests session continuity."""
    url = f"{base}/chat"
    payload = {
        "session_id": session_id,
        "question": "What are the fees for it?",
    }
    try:
        r = requests.post(url, json=payload, timeout=120)
        if r.status_code != 200:
            fail("Follow-up (session continuity)", f"status={r.status_code}")
            return False
        data = r.json()
        if data.get("session_id") != session_id:
            fail("Follow-up (session continuity)", "session_id changed")
            return False
        ok(
            "Follow-up (session continuity)",
            f"resolved_query=\"{data.get('resolved_query', '')[:60]}\"",
        )
        return True
    except Exception as exc:
        fail("Follow-up (session continuity)", str(exc))
        return False


def test_clear_history(base: str, session_id: str) -> bool:
    """DELETE /chat/history/{session_id} — should return 200."""
    url = f"{base}/chat/history/{session_id}"
    try:
        r = requests.delete(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("cleared"):
                ok("Clear history", f"session {session_id[:8]}… cleared")
                return True
            else:
                fail("Clear history", "cleared=false")
                return False
        else:
            fail("Clear history", f"status={r.status_code}")
            return False
    except Exception as exc:
        fail("Clear history", str(exc))
        return False


def test_frontend(frontend_url: str) -> bool:
    """GET frontend_url — should return 200 with HTML content."""
    try:
        r = requests.get(frontend_url, timeout=15)
        if r.status_code == 200 and "<html" in r.text.lower():
            ok("Frontend reachable", f"{frontend_url} → 200")
            return True
        else:
            fail("Frontend reachable", f"status={r.status_code}")
            return False
    except Exception as exc:
        fail("Frontend reachable", str(exc))
        return False


# ── Main ─────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke tests for the CHARUSAT chatbot deployment",
    )
    parser.add_argument(
        "--backend",
        default="http://localhost:8000",
        help="Backend API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--frontend",
        default=None,
        help="Frontend URL to check (optional, e.g. https://your-app.vercel.app)",
    )
    args = parser.parse_args()

    base = args.backend.rstrip("/")
    print(f"\n{BOLD}╔══════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}║   CHARUSAT Chatbot — Smoke Test Suite            ║{RESET}")
    print(f"{BOLD}╚══════════════════════════════════════════════════╝{RESET}")
    print(f"\n  Backend : {CYAN}{base}{RESET}")
    if args.frontend:
        print(f"  Frontend: {CYAN}{args.frontend}{RESET}")
    print()

    # 1. Health
    healthy = test_health(base)
    if not healthy:
        print(f"\n  {YELLOW}⚠ Backend unreachable or unhealthy. Remaining tests skipped.{RESET}\n")
        print_summary()
        return

    # 2. Root
    test_root(base)

    # 3. Chat
    print()
    session_id = test_chat(base)

    # 4. Follow-up
    if session_id:
        test_followup(base, session_id)

    # 5. Clear history
    if session_id:
        test_clear_history(base, session_id)

    # 6. Frontend
    if args.frontend:
        print()
        test_frontend(args.frontend)

    print()
    print_summary()


def print_summary() -> None:
    total = passed + failed
    if failed == 0:
        print(f"  {GREEN}{BOLD}All {total} tests passed ✓{RESET}\n")
    else:
        print(f"  {RED}{BOLD}{failed}/{total} tests failed ✗{RESET}\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
