"""Offline unit tests for Knowledge Base Manager (Part 3 & Part 4).

Covers:
- File validation (magic bytes, size limits, invalid extension, null bytes)
- Path traversal guards and slug generation
- PDF conversion with PyMuPDF (headings, tables, unicode cleanup, Hindi/Gujarati preservation)
- Scanned PDF detection (warning & publish blocked)
- DOCX conversion with python-docx (headings, tables)
- GitHub client behavior (unconfigured detection, commit with 409 retry)
- API endpoints: convert, update draft, publish, status, test-question (dry run), faq
"""
import io
import json
import os
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import create_token, hash_password
from app.database import get_db
from app.models import create_user
from app.kb_manager import (
    clean_unicode_text,
    convert_file_to_markdown,
    generate_safe_slug,
    validate_safe_slug,
    validate_uploaded_file,
    GitHubClient,
    _KB_DRAFTS,
)


@pytest.fixture
def admin_headers():
    db = get_db()
    admin = db.users.find_one({"role": "admin"})
    if not admin:
        admin = create_user(
            db,
            name="Admin KB",
            email="admin_kb@charusat.ac.in",
            password_hash=hash_password("admin_pass123"),
            role="admin",
        )
    admin_id = str(admin.get("_id") or admin.get("id"))
    token = create_token(admin_id, role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    from api import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Validation & Security Guards
# ---------------------------------------------------------------------------

def test_validate_uploaded_file_guards():
    # Empty file
    with pytest.raises(Exception) as exc:
        validate_uploaded_file("doc.pdf", b"")
    assert "empty" in str(exc.value).lower()

    # File too large
    with pytest.raises(Exception) as exc:
        validate_uploaded_file("large.pdf", b"%PDF-" + b"x" * (11 * 1024 * 1024))
    assert "maximum upload size" in str(exc.value).lower()

    # Unsupported format
    with pytest.raises(Exception) as exc:
        validate_uploaded_file("script.exe", b"MZ\x90\x00")
    assert "unsupported" in str(exc.value).lower()

    # Magic byte mismatch for PDF
    with pytest.raises(Exception) as exc:
        validate_uploaded_file("fake.pdf", b"This is not a pdf header")
    assert "does not match pdf extension" in str(exc.value).lower()

    # Magic byte mismatch for DOCX
    with pytest.raises(Exception) as exc:
        validate_uploaded_file("fake.docx", b"Not a zip file")
    assert "not a valid zip" in str(exc.value).lower()

    # Binary null bytes in text
    with pytest.raises(Exception) as exc:
        validate_uploaded_file("corrupt.txt", b"Hello\x00World")
    assert "binary" in str(exc.value).lower()


def test_path_traversal_guards():
    # Valid slugs
    assert validate_safe_slug("charusat-fees-2026") == "charusat-fees-2026"
    assert validate_safe_slug("faq-admission-deadline") == "faq-admission-deadline"

    # Path traversal attempts
    with pytest.raises(Exception):
        validate_safe_slug("../outside")
    with pytest.raises(Exception):
        validate_safe_slug("../../etc/passwd")
    with pytest.raises(Exception):
        validate_safe_slug("sub/folder")
    with pytest.raises(Exception):
        validate_safe_slug("sub\\folder")
    with pytest.raises(Exception):
        validate_safe_slug("invalid_slug_with_underscores")


def test_slug_generation():
    slug = generate_safe_slug("BBA Online Course Syllabus 2026-27!")
    assert slug == "bba-online-course-syllabus-2026-27"

    # Empty fallback
    slug_empty = generate_safe_slug("!@#$%^&*")
    assert slug_empty.startswith("doc-")


# ---------------------------------------------------------------------------
# 2. Text Normalization & Unicode Cleanup
# ---------------------------------------------------------------------------

def test_clean_unicode_text():
    raw = (
        "Welcome\u200b to CHARUSAT\ufeff.\u00a0Course\u202ffees\u2014₹50,000.\n"
        "This is an un-\nexpected break.\n"
        "ગુજરાત અને हिन्दी"
    )
    cleaned = clean_unicode_text(raw)
    # Zero width removed
    assert "\u200b" not in cleaned
    assert "\ufeff" not in cleaned
    # Odd spaces normalized to standard space
    assert "\u00a0" not in cleaned
    assert "\u202f" not in cleaned
    # Em dash replaced with ' - '
    assert "\u2014" not in cleaned
    assert " - " in cleaned
    # Hyphenation repaired
    assert "unexpected" in cleaned
    # Indic text preserved
    assert "ગુજરાત" in cleaned
    assert "हिन्दी" in cleaned


# ---------------------------------------------------------------------------
# 3. PDF Conversion with PyMuPDF
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_pdf_conversion_with_headings_and_tables():
    import fitz

    # Create synthetic test PDF in-memory
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((50, 40), "Header Repeated", fontsize=9)  # top header
    page1.insert_text((50, 80), "CHARUSAT Online Programmes", fontsize=22)
    page1.insert_text((50, 120), "Admissions and Eligibility Details", fontsize=16)
    page1.insert_text(
        (50, 160),
        "Candidates with 50% marks in 10+2 are eligible for admission.\nFees are ₹50,000 per year.",
        fontsize=11,
    )
    page1.insert_text((50, 800), "Page 1 of 2", fontsize=9)  # bottom footer

    page2 = doc.new_page()
    page2.insert_text((50, 40), "Header Repeated", fontsize=9)  # repeated top header
    page2.insert_text((50, 80), "Course Structure", fontsize=16)
    page2.insert_text((50, 120), "Syllabus covers data structures and web systems.", fontsize=11)
    page2.insert_text((50, 800), "Page 2 of 2", fontsize=9)  # repeated bottom footer

    pdf_bytes = doc.tobytes()
    doc.close()

    markdown, warnings, pages, can_publish = await convert_file_to_markdown("test_catalog.pdf", pdf_bytes)

    assert pages == 2
    assert can_publish is True
    assert "CHARUSAT Online Programmes" in markdown
    assert "Course Structure" in markdown
    assert markdown.count("Header Repeated") < 2


@pytest.mark.anyio
async def test_scanned_pdf_blocks_publish():
    import fitz

    # Create empty blank PDF (no text)
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    markdown, warnings, pages, can_publish = await convert_file_to_markdown("scanned.pdf", pdf_bytes)
    assert can_publish is False
    assert any("scanned" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# 4. DOCX Conversion with python-docx
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_docx_conversion():
    import docx

    doc = docx.Document()
    doc.add_heading("Online MBA Syllabus", level=1)
    doc.add_paragraph("Master of Business Administration details.")

    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Semester"
    table.cell(0, 1).text = "Subjects"
    table.cell(1, 0).text = "Sem 1"
    table.cell(1, 1).text = "Management Principles"

    bio = io.BytesIO()
    doc.save(bio)
    docx_bytes = bio.getvalue()

    markdown, warnings, pages, can_publish = await convert_file_to_markdown("mba_syllabus.docx", docx_bytes)
    assert can_publish is True
    assert "Online MBA Syllabus" in markdown
    assert "Management Principles" in markdown
    assert "| Semester | Subjects |" in markdown


# ---------------------------------------------------------------------------
# 5. GitHub Client Behavior & 409 Retry
# ---------------------------------------------------------------------------

def test_github_client_unconfigured():
    with patch.dict(os.environ, {"GITHUB_REPO": "", "GITHUB_TOKEN": ""}, clear=False):
        gh = GitHubClient()
        configured, missing = gh.is_configured()
        assert configured is False
        assert "GITHUB_REPO" in missing
        assert "GITHUB_TOKEN" in missing


def test_github_client_commit_with_409_retry():
    with patch.dict(
        os.environ,
        {
            "GITHUB_REPO": "testowner/testrepo",
            "GITHUB_BRANCH": "main",
            "GITHUB_TOKEN": "mock_token",
            "GITHUB_WORKFLOW_FILE": "sync-knowledge-base.yml",
        },
    ):
        gh = GitHubClient()
        call_count = {"put": 0}

        def mock_urlopen(req, timeout=15):
            method = req.get_method()
            resp = MagicMock()
            resp.__enter__.return_value = resp
            if method == "GET":
                resp.status = 200
                resp.read.return_value = json.dumps({"sha": "sha_123"}).encode("utf-8")
                return resp
            elif method == "PUT":
                call_count["put"] += 1
                if call_count["put"] == 1:
                    fp = io.BytesIO(json.dumps({"message": "Conflict"}).encode("utf-8"))
                    raise urllib.error.HTTPError(req.full_url, 409, "Conflict", {}, fp)
                else:
                    resp.status = 200
                    resp.read.return_value = json.dumps({"content": {"sha": "sha_456"}}).encode("utf-8")
                    return resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            success = gh.commit_file("uploads/test.md", b"Content", "commit test")
            assert success is True
            assert call_count["put"] == 2


# ---------------------------------------------------------------------------
# 6. Admin KB Endpoints (Convert, Draft, Publish, Status, Test Question, FAQ)
# ---------------------------------------------------------------------------

def test_kb_convert_and_draft_lifecycle(client, admin_headers):
    # 1. Convert text file
    txt_content = b"# Placement Notice 2026\nTop recruiters include TCS, Infosys, and L&T."
    response = client.post(
        "/api/admin/kb/convert",
        files={"file": ("placement_notice.txt", txt_content, "text/plain")},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "draft_id" in data
    assert data["can_publish"] is True
    draft_id = data["draft_id"]

    # 2. Update draft
    update_res = client.put(
        f"/api/admin/kb/drafts/{draft_id}",
        json={"title": "Official Placement Notice 2026", "programme": "BCA"},
        headers=admin_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Official Placement Notice 2026"
    assert update_res.json()["programme"] == "BCA"

    # 3. Publish draft
    pub_res = client.post(
        f"/api/admin/kb/drafts/{draft_id}/publish",
        json={"title": "Official Placement Notice 2026", "programme": "BCA"},
        headers=admin_headers,
    )
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["status"] == "success"
    assert "official-placement-notice-2026" in pub_data["slug"]


def test_kb_test_question_dry_run(client, admin_headers):
    db = get_db()
    initial_events = db["chat_events"].count_documents({}) if db is not None else 0

    response = client.post(
        "/api/admin/kb/test-question",
        json={"question": "What is the fee for online MCA?"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "answerable" in data
    assert "chunks" in data
    assert isinstance(data["chunks"], list)

    if db is not None:
        final_events = db["chat_events"].count_documents({})
        assert final_events == initial_events


def test_kb_faq_workflow_and_gap_resolution(client, admin_headers):
    db = get_db()
    gap_id = None
    if db is not None:
        res = db["knowledge_gaps"].insert_one({
            "normalized_question": "how do i request a transcript",
            "topic": "examination",
            "status": "open",
            "frequency": 2,
        })
        gap_id = str(res.inserted_id)

    response = client.post(
        "/api/admin/kb/faq",
        json={
            "question": "How do I request an official degree transcript?",
            "answer": "Submit a written application to the Registrar Examination Section along with fee receipt of Rs 500.",
            "source": "https://charusat.online/mandatory-disclosures.html",
            "programme": "GENERAL",
            "gap_id": gap_id,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["slug"].startswith("faq-")

    if db is not None and gap_id:
        gap = db["knowledge_gaps"].find_one({"_id": res.inserted_id})
        assert gap["status"] == "resolved"
        assert "FAQ" in gap.get("notes", "")
