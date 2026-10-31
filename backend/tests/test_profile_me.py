"""Unit tests for /api/me profile endpoints.

Tests:
  - GET /api/me returns user profile
  - Valid display_name update (200)
  - Empty display_name rejected (422)
  - Display name with HTML rejected (422)
  - Display name with URLs rejected (422)
  - Display name >40 characters rejected (422)
  - Photo chosen without photo_url rejected (422)
  - Photo chosen with photo_url succeeds (200)
  - Initials avatar_type update works (200)
  - Unauthenticated access returns 401
"""
from __future__ import annotations

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient

from api import app
from app.auth import create_token
from app.database import get_db
from app.models import create_user, update_user


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def test_user():
    db = get_db()
    if db is None:
        pytest.skip("MongoDB not available")
    # Clean up any previous test user
    email = "profile_test_user@charusat.ac.in"
    db.users.delete_many({"email": email})
    user = create_user(
        db,
        name="Original Name",
        email=email,
        password_hash="test_hash",
        role="user",
    )
    user_id = str(user.get("_id") or user.get("id"))
    token = create_token(user_id, "user")
    return {"id": user_id, "email": email, "token": token}


def test_unauthenticated_rejected(client):
    """Accessing /api/me without credentials returns 401."""
    resp = client.get("/api/me")
    assert resp.status_code == 401

    resp_patch = client.patch("/api/me", json={"display_name": "New Name", "avatar_type": "initials"})
    assert resp_patch.status_code == 401


def test_get_me_profile(client, test_user):
    """GET /api/me returns user profile with required fields."""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    resp = client.get("/api/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == test_user["id"]
    assert data["email"] == test_user["email"]
    assert data["display_name"] == "Original Name"
    assert data["avatar_type"] == "initials"
    assert data["role"] == "user"


def test_valid_name_update(client, test_user):
    """PATCH /api/me with valid display_name and initials succeeds."""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    payload = {"display_name": "Aarav Patel", "avatar_type": "initials"}
    resp = client.patch("/api/me", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Aarav Patel"
    assert data["avatar_type"] == "initials"


def test_empty_name_rejected(client, test_user):
    """PATCH /api/me with empty or whitespace-only name returns 422."""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    for bad_name in ["", "   ", "\t\n"]:
        resp = client.patch(
            "/api/me",
            json={"display_name": bad_name, "avatar_type": "initials"},
            headers=headers,
        )
        assert resp.status_code == 422


def test_name_too_long_rejected(client, test_user):
    """PATCH /api/me with >40 chars returns 422."""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    resp = client.patch(
        "/api/me",
        json={"display_name": "A" * 41, "avatar_type": "initials"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_html_in_name_rejected(client, test_user):
    """PATCH /api/me with HTML characters returns 422."""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    for bad_name in ["<script>alert(1)</script>", "<b>User</b>", "User <test>"]:
        resp = client.patch(
            "/api/me",
            json={"display_name": bad_name, "avatar_type": "initials"},
            headers=headers,
        )
        assert resp.status_code == 422


def test_url_in_name_rejected(client, test_user):
    """PATCH /api/me with URLs returns 422."""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    for bad_name in ["User https://evil.com", "http://spam.org", "www.attacker.com"]:
        resp = client.patch(
            "/api/me",
            json={"display_name": bad_name, "avatar_type": "initials"},
            headers=headers,
        )
        assert resp.status_code == 422


def test_photo_chosen_without_photo_url_rejected(client, test_user):
    """PATCH /api/me with avatar_type='photo' when user has no photo returns 422."""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    resp = client.patch(
        "/api/me",
        json={"display_name": "Valid Name", "avatar_type": "photo"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert "no photo URL" in resp.json()["detail"]


def test_photo_chosen_with_photo_url_succeeds(client, test_user):
    """PATCH /api/me with avatar_type='photo' when user HAS photo URL succeeds."""
    db = get_db()
    update_user(db, test_user["id"], {"photo_url": "https://lh3.googleusercontent.com/a/sample"})

    headers = {"Authorization": f"Bearer {test_user['token']}"}
    resp = client.patch(
        "/api/me",
        json={"display_name": "Photo User", "avatar_type": "photo"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["avatar_type"] == "photo"
    assert data["photo_url"] == "https://lh3.googleusercontent.com/a/sample"
