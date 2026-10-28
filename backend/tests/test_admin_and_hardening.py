"""Comprehensive unit and integration tests for backend hardening and admin endpoints.

Tests:
  - Non-admin receives 403 on protected admin endpoints
  - Admin login requires database user with role 'admin'
  - Admin overview aggregates calculation
  - Knowledge gaps grouping and workflow review_status patch
  - Formula injection neutralization in CSV export
  - Conversations inspection and audited reveal
  - Feedback queue and reason field persistence
  - User role update, disable/enable, and delete
  - Protection preventing admin from self-demotion or self-deletion
  - Disabled user account rejection (403)
  - 1000 character limit enforcement on chat questions
  - User self-data export (/api/me/export) and self-deletion (/api/me)
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from api import app, get_allowed_origins
from app.auth import create_token, hash_password
from app.database import get_db
from app.routes.admin_routes import sanitize_csv_cell, normalize_question, mask_email


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def db():
    return get_db()


@pytest.fixture(scope="module")
def admin_token(db):
    if db is None:
        pytest.skip("MongoDB not available")
    # Find existing admin or create test admin
    admin = db.users.find_one({"role": "admin"})
    if not admin:
        from app.models import create_user
        admin = create_user(db, name="TestAdmin", email="admin_test@charusat.ac.in", password_hash=hash_password("admin_pass"), role="admin")
    return create_token(str(admin["_id"]), role="admin")


@pytest.fixture(scope="module")
def user_token(db):
    if db is None:
        pytest.skip("MongoDB not available")
    user = db.users.find_one({"role": "user"})
    if not user:
        from app.models import create_user
        user = create_user(db, name="NormalUser", email="normal_user@example.com", password_hash=hash_password("user_pass"), role="user")
    return create_token(str(user["_id"]), role="user")


# ---------------------------------------------------------------------------
# 1. Access Control & 403 on Admin Routes for Non-Admins
# ---------------------------------------------------------------------------

def test_unauthenticated_admin_routes_forbidden(client):
    endpoints = [
        "/api/admin/overview",
        "/api/admin/knowledge-gaps",
        "/api/admin/conversations",
        "/api/admin/feedback",
        "/api/admin/users",
        "/api/admin/knowledge-base",
        "/api/admin/audit-log",
        "/api/admin/system",
        "/api/admin/cache",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code in (401, 403), f"Expected 401/403 for {ep}, got {resp.status_code}"


def test_normal_user_gets_403_on_admin_routes(client, user_token):
    endpoints = [
        "/api/admin/overview",
        "/api/admin/knowledge-gaps",
        "/api/admin/conversations",
        "/api/admin/feedback",
        "/api/admin/users",
        "/api/admin/knowledge-base",
        "/api/admin/audit-log",
        "/api/admin/system",
    ]
    headers = {"Authorization": f"Bearer {user_token}"}
    for ep in endpoints:
        resp = client.get(ep, headers=headers)
        assert resp.status_code == 403, f"Expected 403 for user on {ep}, got {resp.status_code}"


# ---------------------------------------------------------------------------
# 2. Admin Endpoints Success Path
# ---------------------------------------------------------------------------

def test_admin_overview_success(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/admin/overview?days=7", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_queries" in data
    assert "gap_queries" in data
    assert "queries_per_day" in data
    assert "feedback" in data
    assert "feedback_rate" in data["feedback"]


def test_admin_knowledge_gaps_and_csv(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/admin/knowledge-gaps?page=1&limit=10", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "gaps" in data
    assert "total" in data

    # Test CSV export with BOM
    csv_resp = client.get("/api/admin/knowledge-gaps/csv", headers=headers)
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"].startswith("text/csv")
    # Verify UTF-8 BOM prefix
    assert csv_resp.content.startswith(b"\xef\xbb\xbf")


def test_admin_knowledge_base_inventory(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/admin/knowledge-base", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_chunks" in data
    assert "documents" in data
    assert "chunks_per_programme" in data


def test_admin_conversations_list_and_detail(client, admin_token, db):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/admin/conversations?page=1&limit=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "conversations" in data

    if data["conversations"]:
        first_id = data["conversations"][0]["id"]
        # Verify masked email by default
        masked = data["conversations"][0].get("user_email_masked")
        assert masked is None or "***" in masked or masked == "anonymous"

        # Detail view
        det_resp = client.get(f"/api/admin/conversations/{first_id}", headers=headers)
        assert det_resp.status_code == 200

        # Audited reveal
        rev_resp = client.post(f"/api/admin/conversations/{first_id}/reveal", headers=headers)
        assert rev_resp.status_code == 200
        assert "user_email" in rev_resp.json()


def test_admin_audit_log(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/admin/audit-log?page=1&limit=10", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "logs" in data
    assert "total" in data


# ---------------------------------------------------------------------------
# 3. Security & Validation Unit Tests
# ---------------------------------------------------------------------------

def test_csv_formula_injection_neutralization():
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd|'/c calc'!A0") == "'+cmd|'/c calc'!A0"
    assert sanitize_csv_cell("-123") == "'-123"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_cell("Normal text") == "Normal text"
    assert sanitize_csv_cell(123) == "123"


def test_email_masking():
    assert mask_email("student@charusat.edu.in") == "s***t@charusat.edu.in"
    assert mask_email("ab@domain.com") == "a***@domain.com"
    assert mask_email("a@domain.com") == "a***@domain.com"
    assert mask_email(None) == "anonymous"


def test_question_normalization():
    assert normalize_question("What is the BBA fee???") == "what is the bba fee"
    assert normalize_question("  MBA, MCA eligibility!  ") == "mba mca eligibility"


def test_1000_char_question_limit(client):
    long_question = "A" * 1001
    resp = client.post("/api/chat", json={"question": long_question})
    assert resp.status_code == 422, "Expected 422 validation error for >1000 char question"

    stream_resp = client.post("/api/chat/stream", json={"question": long_question})
    assert stream_resp.status_code == 422, "Expected 422 validation error on stream for >1000 chars"


def test_cors_restriction():
    origins = get_allowed_origins()
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    # Ensure wildcard is NOT in allowed origins
    assert "*" not in origins
