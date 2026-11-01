"""Pytest root configuration and database isolation fixture.

Guarantees tests NEVER write to production or default databases.
Uses in-memory mongomock by default, with a unique throwaway database name guard.
"""

from __future__ import annotations

import os
import sys
import uuid
import pytest
from pathlib import Path

# 1. Enforce unique throwaway database name BEFORE any app import
TEST_DB_NAME = f"charusat_test_throwaway_{uuid.uuid4().hex[:8]}"
os.environ["MONGODB_DB"] = TEST_DB_NAME
os.environ["USE_MONGOMOCK"] = "1"


# 2. Guard Check: Immediately abort if target equals the real default
if os.environ.get("MONGODB_DB") in ("charusat_assistant", "charusat", "", None):
    pytest.exit(
        "CRITICAL SECURITY ABORT: MONGODB_DB is pointing to real/default database name! "
        "Tests must run on an isolated throwaway database.",
        returncode=3,
    )

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


@pytest.fixture(autouse=True)
def ensure_db_isolation(monkeypatch):
    """Ensure every test runs against the isolated test database."""
    monkeypatch.setenv("MONGODB_DB", TEST_DB_NAME)
    monkeypatch.setenv("USE_MONGOMOCK", "1")
    if os.environ.get("MONGODB_DB") in ("charusat_assistant", "charusat", "", None):
        pytest.exit("CRITICAL: MONGODB_DB reset to production name during test run!", returncode=3)


def pytest_sessionfinish(session, exitstatus):
    """Drop the throwaway database at session end if real MongoDB was touched."""
    try:
        from app import database
        client = getattr(database, "_client", None)
        if client is not None and hasattr(client, "drop_database"):
            # Only drop if it is indeed our unique throwaway database
            if TEST_DB_NAME.startswith("charusat_test_throwaway_"):
                client.drop_database(TEST_DB_NAME)
    except Exception:
        pass

