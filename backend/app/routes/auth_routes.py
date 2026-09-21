"""Authentication API routes.

Endpoints:
  POST /api/auth/signup      — create account (email/password)
  POST /api/auth/login       — email/password login
  POST /api/auth/logout      — logout (client-side token removal)
  GET  /api/auth/me          — current user info
  POST /api/auth/google      — Google OAuth login/signup
  POST /api/auth/dev-login   — development-only auto-login
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import (
    create_token,
    decode_token,
    get_current_user,
    get_dev_admin_email,
    hash_password,
    is_dev_auto_login_enabled,
    seed_dev_admin,
    verify_google_token,
    verify_password,
)
from app.database import get_db
from app.models import (
    create_user,
    find_user_by_email,
    find_user_by_google_id,
    update_user,
)
from app.utils import logger

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., min_length=1)


class GuestConversation(BaseModel):
    """A guest conversation to migrate after signup/login."""
    messages: List[Dict[str, Any]] = []


class AuthResponse(BaseModel):
    token: str
    user: Dict[str, Any]


class UserResponse(BaseModel):
    user: Dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """Create a new account with email and password."""
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please try again later.",
        )

    # Validate email format
    email = request.email.lower().strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format",
        )

    # Check if user already exists
    existing = find_user_by_email(db, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Determine role
    admin_email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    role = "admin" if admin_email and email == admin_email else "user"

    # Create user
    password_hash = hash_password(request.password)
    user = create_user(
        db,
        name=request.name.strip(),
        email=email,
        password_hash=password_hash,
        role=role,
    )

    # Remove sensitive fields
    user.pop("password_hash", None)

    token = create_token(user["id"], user["role"])
    return AuthResponse(token=token, user=user)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login with email and password."""
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please try again later.",
        )

    email = request.email.lower().strip()
    user = find_user_by_email(db, email)

    if not user or not user.get("password_hash"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Remove sensitive fields
    user.pop("password_hash", None)

    token = create_token(user["id"], user["role"])
    return AuthResponse(token=token, user=user)


@router.post("/logout")
async def logout():
    """Logout. Token invalidation is handled client-side."""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    """Get the current authenticated user's information."""
    user.pop("password_hash", None)
    return UserResponse(user=user)


@router.post("/google", response_model=AuthResponse)
async def google_auth(request: GoogleAuthRequest):
    """Authenticate with Google OAuth credential."""
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not google_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google authentication is not configured",
        )

    # Verify the Google token
    google_info = await verify_google_token(request.credential)
    if not google_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        )

    # Find existing user by Google ID or email
    user = find_user_by_google_id(db, google_info["google_id"])
    if not user:
        user = find_user_by_email(db, google_info["email"])

    if user:
        # Link Google ID if not already linked
        updates = {}
        if not user.get("google_id"):
            updates["google_id"] = google_info["google_id"]
        if google_info.get("avatar") and not user.get("avatar"):
            updates["avatar"] = google_info["avatar"]
        if updates:
            user = update_user(db, user["id"], updates)
    else:
        # Create new user from Google info
        admin_email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
        role = "admin" if admin_email and google_info["email"].lower() == admin_email else "user"

        user = create_user(
            db,
            name=google_info["name"],
            email=google_info["email"],
            google_id=google_info["google_id"],
            avatar=google_info.get("avatar"),
            role=role,
        )

    user.pop("password_hash", None)
    token = create_token(user["id"], user["role"])
    return AuthResponse(token=token, user=user)


@router.post("/dev-login", response_model=AuthResponse)
async def dev_login():
    """Development-only auto-login.

    SECURITY: This endpoint ONLY works when:
      1. The server is running in a development environment
      2. DEV_AUTO_LOGIN env var is explicitly set to "true"
      3. ADMIN_EMAIL is configured

    It will NOT work in production deployments.
    """
    # Safety check: refuse in production
    env = os.getenv("NODE_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if env in ("production", "prod"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login is not available in production",
        )

    if not is_dev_auto_login_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev auto-login is not enabled",
        )

    admin_email = get_dev_admin_email()
    if not admin_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ADMIN_EMAIL is not configured",
        )

    # Seed the admin user if needed
    user = seed_dev_admin()
    if not user:
        db = get_db()
        if db:
            user = find_user_by_email(db, admin_email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create or find dev admin user",
        )

    user.pop("password_hash", None)
    token = create_token(user["id"], user.get("role", "admin"))
    logger.info("[DEV] Auto-login for: %s", admin_email)
    return AuthResponse(token=token, user=user)
