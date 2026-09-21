"""Authentication module for the CHARUSAT Online Course Assistant.

Provides:
  - JWT token creation and validation
  - Password hashing with passlib/bcrypt
  - FastAPI dependencies for protected routes
  - Development-only auto-login
  - Google OAuth token verification
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.database import get_db
from app.models import (
    create_user,
    find_user_by_email,
    find_user_by_id,
    find_user_by_google_id,
)
from app.utils import logger

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _get_jwt_secret() -> str:
    """Return JWT secret. Falls back to a development-only default."""
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        # Development fallback — never use in production
        secret = "charusat-dev-jwt-secret-change-in-production"
        logger.warning("JWT_SECRET not set — using insecure development default")
    return secret


JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 1 week

import bcrypt

def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    try:
        pw_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hashed_bytes)
    except Exception as exc:
        logger.warning("Password verification error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

def create_token(user_id: str, role: str = "user") -> str:
    """Create a JWT token for the given user."""
    secret = _get_jwt_secret()
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token. Returns payload or None."""
    secret = _get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as exc:
        logger.debug("JWT decode failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

# Optional bearer — does not throw if no token is present
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Dict[str, Any]:
    """FastAPI dependency: requires a valid JWT. Raises 401 if missing/invalid."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    user = find_user_by_id(db, payload["sub"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """FastAPI dependency: returns the user if authenticated, None for guests."""
    if credentials is None:
        return None

    payload = decode_token(credentials.credentials)
    if payload is None:
        return None

    db = get_db()
    if db is None:
        return None

    return find_user_by_id(db, payload["sub"])


async def require_admin(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """FastAPI dependency: requires the user to have admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ---------------------------------------------------------------------------
# Development auto-login
# ---------------------------------------------------------------------------

def is_dev_auto_login_enabled() -> bool:
    """Check if development auto-login is enabled."""
    env = os.getenv("DEV_AUTO_LOGIN", "false").strip().lower()
    return env in ("true", "1", "yes")


def get_dev_admin_email() -> Optional[str]:
    """Return the configured development admin email."""
    return (os.getenv("ADMIN_EMAIL") or "").strip() or None


def seed_dev_admin() -> Optional[Dict[str, Any]]:
    """Create the dev admin user if DEV_AUTO_LOGIN is enabled and user doesn't exist.

    This is only called during development startup. It is idempotent.
    Returns the admin user dict or None.
    """
    if not is_dev_auto_login_enabled():
        return None

    email = get_dev_admin_email()
    if not email:
        logger.warning("DEV_AUTO_LOGIN is true but ADMIN_EMAIL is not set")
        return None

    db = get_db()
    if db is None:
        logger.warning("Cannot seed dev admin: MongoDB not available")
        return None

    existing = find_user_by_email(db, email)
    if existing:
        # Ensure admin role
        if existing.get("role") != "admin":
            from app.models import update_user
            update_user(db, existing["id"], {"role": "admin"})
            logger.info("Updated existing user to admin: %s", email)
        return find_user_by_email(db, email)

    # Create the admin user with a default password
    user = create_user(
        db,
        name="Admin",
        email=email,
        password_hash=hash_password("admin123"),
        role="admin",
    )
    logger.info("Seeded development admin user: %s", email)
    return user


# ---------------------------------------------------------------------------
# Google OAuth verification
# ---------------------------------------------------------------------------

async def verify_google_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a Google ID token and return user info.

    Uses Google's tokeninfo endpoint. Returns None on failure.
    """
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
            )
            if resp.status_code != 200:
                logger.warning("Google token verification failed: %s", resp.status_code)
                return None

            data = resp.json()
            # Verify the client ID matches our configured one
            expected_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
            if expected_client_id and data.get("aud") != expected_client_id:
                logger.warning("Google token audience mismatch")
                return None

            return {
                "google_id": data.get("sub"),
                "email": data.get("email"),
                "name": data.get("name", data.get("email", "").split("@")[0]),
                "avatar": data.get("picture"),
                "email_verified": data.get("email_verified") == "true",
            }
    except Exception as exc:
        logger.error("Google token verification error: %s", exc)
        return None
