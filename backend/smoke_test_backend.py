#!/usr/bin/env python3
"""
CHARUSAT Online Course Chatbot — Full Backend Smoke Test
=========================================================
Tests:
  TEST 1  — Backend startup (server process)
  TEST 2  — Health check endpoint
  TEST 3  — ChromaDB connection + document count
  TEST 4  — Vector retrieval (semantic search)
  TEST 5  — RAG + LLM pipeline (end-to-end)
  TEST 6  — Chat API endpoint (HTTP)
  TEST 7  — Session continuity / follow-up question

Usage (from project root or backend/):
    python backend/smoke_test_backend.py

The script starts the FastAPI server itself, runs all tests, then stops it.
No arguments required for local testing.

IMPORTANT: API keys are NEVER printed.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# ── Force UTF-8 on Windows ──────────────────────────────────────────────────
if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Path setup ───────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent          # backend/
PROJECT_ROOT = SCRIPT_DIR.parent                      # project root

# Add backend dir to sys.path so "from app.*" imports work
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ── Counters ─────────────────────────────────────────────────────────────────
_passed = 0
_failed = 0
_results: list[tuple[str, bool, str]] = []   # (name, passed, detail)

SEPARATOR = "-" * 60


def _ok(name: str, detail: str = "") -> None:
    global _passed
    _passed += 1
    _results.append((name, True, detail))
    print(f"  {GREEN}PASS{RESET}  {name}")
    if detail:
        print(f"         {CYAN}{detail}{RESET}")


def _fail(name: str, detail: str = "") -> None:
    global _failed
    _failed += 1
    _results.append((name, False, detail))
    print(f"  {RED}FAIL{RESET}  {name}")
    if detail:
        print(f"         {YELLOW}{detail}{RESET}")


def _header(title: str) -> None:
    print(f"\n{BOLD}{SEPARATOR}{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{BOLD}{SEPARATOR}{RESET}")


# ==============================================================================
# TEST 3 -- ChromaDB direct connection
# ==============================================================================
def test_chromadb_direct() -> None:
    """
    Directly connect to the ChromaDB persistent database and verify:
      - The SQLite file exists
      - At least one collection is present
      - The collection has documents
    """
    _header("TEST 3 -- ChromaDB Direct Connection")

    from app.config import VECTOR_DB_DIR

    # Check the DB directory and SQLite file
    db_path = Path(VECTOR_DB_DIR)
    sqlite_path = db_path / "chroma.sqlite3"

    print(f"  ChromaDB path : {db_path}")
    print(f"  SQLite file   : {sqlite_path}")

    if not db_path.exists():
        _fail("ChromaDB path exists", f"Directory not found: {db_path}")
        return
    if not sqlite_path.exists():
        _fail("ChromaDB SQLite file", f"chroma.sqlite3 not found in {db_path}")
        return

    _ok("ChromaDB path exists", str(db_path))

    # Load via EmbeddingStore (same code path as the real backend)
    try:
        from app.embeddings import EmbeddingStore
        store = EmbeddingStore()
        vector_store = store.load_vector_store()
        collection = vector_store._collection
        count = collection.count()
        collection_name = collection.name

        print(f"  Collection    : {collection_name}")
        print(f"  Documents     : {count}")

        _ok("ChromaDB connected", f"collection={collection_name}")

        if count == 0:
            _fail("ChromaDB documents", "Collection is EMPTY -- no documents found!")
        else:
            _ok("ChromaDB documents", f"{count} chunks stored")

    except Exception as exc:
        _fail("ChromaDB connected", f"{type(exc).__name__}: {exc}")


# ==============================================================================
# TEST 4 -- Vector retrieval (semantic search)
# ==============================================================================
def test_vector_retrieval() -> None:
    """
    Perform a real semantic search against ChromaDB using the SAME embedding
    model as the project.  No LLM is involved here.
    """
    _header("TEST 4 -- Vector Retrieval (Semantic Search)")

    query = "What online courses are available at CHARUSAT?"
    print(f"  Query: \"{query}\"")

    try:
        from app.embeddings import EmbeddingStore
        from app.retriever import RAGRetriever

        store = EmbeddingStore()
        vector_store = store.load_vector_store()
        retriever = RAGRetriever(vector_store)
        results = retriever.retrieve(query)

        print(f"  Retrieved chunks : {len(results)}")

        if not results:
            _fail("Vector retrieval", "No chunks returned -- check ChromaDB content")
            return

        _ok("Vector retrieval", f"{len(results)} relevant chunks returned")

        # Print preview of each chunk
        for i, (doc, score) in enumerate(results, 1):
            source = doc.metadata.get("source", "unknown")
            page   = doc.metadata.get("page", "n/a")
            prog   = doc.metadata.get("program_name", "")
            preview = doc.page_content.strip()[:120].replace("\n", " ")
            print(
                f"\n  [{i}] score={score:.3f}  source={source}"
                + (f"  page={page}" if str(page) != "n/a" else "")
                + (f"  prog={prog}" if prog else "")
                + f"\n       {CYAN}{preview}...{RESET}"
            )

    except Exception as exc:
        _fail("Vector retrieval", f"{type(exc).__name__}: {exc}")


# ==============================================================================
# TEST 5 -- Full RAG + LLM pipeline
# ==============================================================================
def test_rag_llm() -> None:
    """
    Run a real question through the complete RAG chain:
      retrieval -> conflict detection -> context build -> LLM -> answer
    """
    _header("TEST 5 -- RAG + LLM Pipeline (End-to-End)")

    question = "What courses are available in the CHARUSAT online programs?"
    print(f"  Question: \"{question}\"")

    try:
        from app.embeddings import EmbeddingStore
        from app.llm import LLMClient
        from app.rag_chain import RAGChain
        from app.retriever import RAGRetriever
        from app.config import get_api_key, get_groq_api_key

        # Report API key presence WITHOUT exposing values
        google_key = get_api_key()
        groq_key   = get_groq_api_key()
        print(f"  GOOGLE_API_KEY : {'SET' if google_key else 'NOT SET (commented out or missing)'}")
        print(f"  GROQ_API_KEY   : {'SET' if groq_key else 'NOT SET'}")

        store = EmbeddingStore()
        vector_store = store.load_vector_store()
        retriever    = RAGRetriever(vector_store)
        llm_client   = LLMClient()
        rag_chain    = RAGChain(retriever, llm_client)

        answer, retrieved = rag_chain.answer(question)
        status = rag_chain.last_status

        print(f"\n  LLM status     : {CYAN}{status}{RESET}")
        print(f"  Sources used   : {len(retrieved)}")
        print(f"\n  Answer preview :")
        print(f"  {CYAN}{answer[:400]}{'...' if len(answer) > 400 else ''}{RESET}")

        if not answer or answer.strip() == "":
            _fail("RAG + LLM", "Empty answer returned")
            return

        _ok("RAG + LLM pipeline", f"status={status}  answer_len={len(answer)}")

    except Exception as exc:
        _fail("RAG + LLM pipeline", f"{type(exc).__name__}: {exc}")


# ==============================================================================
# Server management helpers (TEST 1, 2, 6, 7)
# ==============================================================================

def _start_server(port: int = 8765) -> Optional[subprocess.Popen]:
    """Start uvicorn in a subprocess; return the Popen object or None.

    IMPORTANT: stdout/stderr must NOT use subprocess.PIPE without the parent
    actively reading them.  On Windows the pipe buffer (~64 KB) fills quickly
    with uvicorn's verbose logging, causing the child process to block on
    stdout writes — resulting in a hang that looks like a timeout.  We redirect
    stdout to DEVNULL and stderr to a temp log file for post-mortem diagnostics.
    """
    python_exe = sys.executable
    cmd = [
        python_exe, "-m", "uvicorn",
        "api:app",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--log-level", "warning",
    ]
    try:
        # Stderr goes to a temp file so _stop_server can read it on failure.
        stderr_log = SCRIPT_DIR / "smoke_test_server.log"
        stderr_fh = open(stderr_log, "w", encoding="utf-8", errors="replace")
        proc = subprocess.Popen(
            cmd,
            cwd=str(SCRIPT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=stderr_fh,
        )
        proc._stderr_fh = stderr_fh          # stash handle for cleanup
        proc._stderr_log = str(stderr_log)    # stash path for diagnostics
        return proc
    except Exception as exc:
        print(f"  {RED}Could not launch uvicorn: {exc}{RESET}")
        return None



def _wait_for_server(port: int, timeout: float = 120.0) -> bool:
    """Poll the /health endpoint until the server is ready or timeout."""
    import urllib.request
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2.0)
    return False


def _stop_server(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=8)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    # Close the stderr log file handle
    fh = getattr(proc, "_stderr_fh", None)
    if fh:
        try:
            fh.close()
        except Exception:
            pass


# ==============================================================================
# TEST 1 -- Backend startup
# ==============================================================================
def test_backend_startup(port: int) -> Optional[subprocess.Popen]:
    _header("TEST 1 -- Backend Startup")
    print(f"  Starting uvicorn on port {port}...")

    proc = _start_server(port)
    if proc is None:
        _fail("Backend startup", "Failed to launch uvicorn process")
        return None

    ready = _wait_for_server(port, timeout=120.0)
    if ready:
        _ok("Backend startup", f"uvicorn running on port {port}")
        return proc
    else:
        # Collect stderr from the log file for diagnosis
        _stop_server(proc)
        err = "(could not read stderr)"
        log_path = getattr(proc, "_stderr_log", None)
        if log_path:
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    err = f.read().strip()[-800:]
            except Exception:
                pass
        _fail("Backend startup", f"Server did not become ready in 120s\n  stderr tail:\n{err}")
        return None


# ==============================================================================
# TEST 2 -- Health check
# ==============================================================================
def test_health_endpoint(base: str) -> bool:
    _header("TEST 2 -- Health Check Endpoint")
    import urllib.request
    import json as _json

    url = f"{base}/health"
    print(f"  GET {url}")
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            body = resp.read().decode()
            data = _json.loads(body)
            docs = data.get("vector_store_documents", -1)
            status = data.get("status", "")
            print(f"  Response: status={status}  vector_store_documents={docs}")
            if status == "ok" and docs > 0:
                _ok("Health check", f"status=ok  docs={docs}")
                return True
            elif docs == 0:
                _fail("Health check", "Vector store is EMPTY (docs=0)")
                return False
            else:
                _fail("Health check", f"Unexpected response: {body[:200]}")
                return False
    except Exception as exc:
        _fail("Health check", str(exc))
        return False


# ==============================================================================
# TEST 6 -- Chat API endpoint
# ==============================================================================
def test_chat_endpoint(base: str) -> Optional[str]:
    _header("TEST 6 -- Chat API Endpoint")
    import urllib.request
    import urllib.error
    import json as _json

    url = f"{base}/chat"
    payload = _json.dumps({"question": "What online programmes does CHARUSAT offer?"}).encode()
    print(f"  POST {url}")
    print(f"  Payload: {{\"question\": \"What online programmes does CHARUSAT offer?\"}}")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = resp.read().decode()
            data = _json.loads(body)

        session_id    = data.get("session_id", "")
        answer        = data.get("answer", "")

        missing = []
        if not session_id: missing.append("session_id")
        if not answer:     missing.append("answer")

        for hidden in ("sources", "resolved_query", "llm_status"):
            if hidden in data:
                missing.append(f"leaked field '{hidden}'")

        print(f"  session_id     : {session_id[:8]}...")
        print(f"  answer_len     : {len(answer)}")
        print(f"  answer preview : {CYAN}{answer[:300]}{'...' if len(answer)>300 else ''}{RESET}")

        if missing:
            _fail("Chat endpoint", f"Missing fields: {missing}")
            return None

        _ok("Chat endpoint", f"HTTP 200  session={session_id[:8]}...")
        return session_id

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:400]
        _fail("Chat endpoint", f"HTTP {exc.code}: {body}")
        return None
    except Exception as exc:
        _fail("Chat endpoint", f"{type(exc).__name__}: {exc}")
        return None


# ==============================================================================
# TEST 7 -- Session continuity / follow-up
# ==============================================================================
def test_session_followup(base: str, session_id: str) -> None:
    _header("TEST 7 -- Session Continuity (Follow-up Question)")
    import urllib.request
    import urllib.error
    import json as _json

    url = f"{base}/chat"
    payload = _json.dumps({
        "session_id": session_id,
        "question": "What are their fees?",
    }).encode()

    print(f"  Session ID : {session_id[:8]}...")
    print(f"  Follow-up  : \"What are their fees?\"")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = resp.read().decode()
            data = _json.loads(body)

        returned_session = data.get("session_id", "")
        answer           = data.get("answer", "")

        print(f"  answer preview : {CYAN}{answer[:250]}{'...' if len(answer)>250 else ''}{RESET}")

        if returned_session != session_id:
            _fail("Session continuity", f"session_id changed: {returned_session}")
            return
        if not answer:
            _fail("Session continuity", "Empty answer for follow-up question")
            return

        _ok("Session continuity", "session preserved")

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:300]
        _fail("Session continuity", f"HTTP {exc.code}: {body}")
    except Exception as exc:
        _fail("Session continuity", f"{type(exc).__name__}: {exc}")


# ==============================================================================
# Summary
# ==============================================================================
def _print_summary() -> None:
    total = _passed + _failed
    print(f"\n{'=' * 60}")
    print("  SMOKE TEST SUMMARY")
    print(f"{'=' * 60}\n")

    label_width = max(len(r[0]) for r in _results) + 2
    for name, passed, detail in _results:
        icon  = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {icon}  {name:<{label_width}}")

    print()
    if _failed == 0:
        print(f"  {GREEN}{BOLD}ALL {total} BACKEND TESTS PASSED{RESET}\n")
        sys.exit(0)
    else:
        print(f"  {RED}{BOLD}BACKEND TEST FAILED -- {_failed}/{total} tests failed{RESET}\n")
        sys.exit(1)


# ==============================================================================
# Main
# ==============================================================================
def main() -> None:
    PORT = 8765   # use a non-standard port to avoid conflicts with port 8000

    print(f"\n{'=' * 54}")
    print("   CHARUSAT Backend -- Full Smoke Test Suite")
    print(f"{'=' * 54}")
    print(f"\n  Project root : {PROJECT_ROOT}")
    print(f"  Backend dir  : {SCRIPT_DIR}")
    print(f"  Test port    : {PORT}\n")

    # -- HTTP SERVER TESTS (run FIRST to avoid SQLite lock contention) ---------
    # IMPORTANT: If in-process tests (3/4/5) load ChromaDB before the server
    # starts, the parent process holds SQLite file locks that block the uvicorn
    # subprocess from opening the same database. Running server tests first
    # avoids this entirely.

    # TEST 1 -- Start server
    proc = test_backend_startup(PORT)
    base = f"http://127.0.0.1:{PORT}"

    if proc is None:
        _header("TEST 2, 6, 7 -- SKIPPED (server did not start)")
        _fail("Health check",      "Skipped -- server did not start")
        _fail("Chat endpoint",     "Skipped -- server did not start")
        _fail("Session continuity","Skipped -- server did not start")
    else:
        try:
            # TEST 2 -- Health check
            test_health_endpoint(base)

            # TEST 6 -- Chat API
            session_id = test_chat_endpoint(base)

            # TEST 7 -- Session continuity
            if session_id:
                test_session_followup(base, session_id)
            else:
                _header("TEST 7 -- SKIPPED (no session_id from TEST 6)")
                _fail("Session continuity", "Skipped -- chat endpoint did not return a session_id")

        finally:
            print(f"\n  Stopping test server...")
            _stop_server(proc)

    # -- DIRECT IN-PROCESS TESTS (after server is stopped) ---------------------

    # TEST 3 -- ChromaDB direct
    test_chromadb_direct()

    # TEST 4 -- Vector retrieval
    test_vector_retrieval()

    # TEST 5 -- RAG + LLM
    test_rag_llm()

    _print_summary()


if __name__ == "__main__":
    main()
