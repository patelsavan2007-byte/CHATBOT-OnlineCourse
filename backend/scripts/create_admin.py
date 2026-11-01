#!/usr/bin/env python3
"""create_admin.py - Helper script to create or update an administrator account in MongoDB."""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.database import init_mongodb, get_db
from app.auth import hash_password
from app.models import find_user_by_email, create_user, update_user


def create_or_update_admin(email: str, password: str, name: str = "Test Admin") -> dict:
    """Create a new admin user or update existing user with password and admin role."""
    clean_email = email.strip().lower()
    db = init_mongodb()
    if db is None:
        raise RuntimeError("Failed to connect to MongoDB. Check MONGODB_URI in backend/.env")

    hashed = hash_password(password)
    existing = find_user_by_email(db, clean_email)

    if existing:
        updates = {
            "role": "admin",
            "password_hash": hashed,
            "name": name,
            "is_disabled": False,
        }
        update_user(db, existing["id"], updates)
        updated = find_user_by_email(db, clean_email)
        print(f"[OK] Updated existing user to admin: {clean_email}")
        return updated
    else:
        user = create_user(
            db,
            name=name,
            email=clean_email,
            password_hash=hashed,
            role="admin",
        )
        print(f"[OK] Created new admin user: {clean_email}")
        return user


def main():
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@charusat.ac.in"
    password = sys.argv[2] if len(sys.argv) > 2 else "charusat@1234"
    name = sys.argv[3] if len(sys.argv) > 3 else "Test Admin"

    print("=" * 60)
    print("CHARUSAT Assistant - Create / Update Admin Account")
    print("=" * 60)
    print(f"Target Email : {email}")
    print(f"Display Name : {name}")
    print("Role         : admin")
    print("-" * 60)

    try:
        user = create_or_update_admin(email, password, name)
        print("\nSuccess! Admin account is ready to use.")
        print(f"Login URL    : /admin/login")
        print(f"Email        : {user['email']}")
        print("Password     : (the password you provided)")
        print("=" * 60)
        return 0
    except Exception as exc:
        print(f"\n[ERROR] Failed to create admin: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

