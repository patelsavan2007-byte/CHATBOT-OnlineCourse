#!/usr/bin/env python3
"""remove_test_records.py - Safely identify and clean up leftover test records in MongoDB.

By default, runs in DRY RUN mode and prints records without deleting anything.
Pass --apply to execute the deletion of only the listed record IDs.
NEVER deletes admin@charusat.ac.in or patelsavan2007@gmail.com.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from bson import ObjectId

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.database import init_mongodb

PROTECTED_EMAILS = frozenset({
    "admin@charusat.ac.in",
    "patelsavan2007@gmail.com",
})


def find_test_records(db):
    """Find leftover test users, testclient audit logs, and empty test conversations."""
    # 1. Users with "test" in email (strictly excluding protected emails)
    candidate_users = list(db.users.find({"email": {"$regex": "test", "$options": "i"}}))
    test_users = [
        u for u in candidate_users
        if u.get("email", "").lower().strip() not in PROTECTED_EMAILS
    ]

    # 2. Audit entries created by testclient
    test_audits = list(db.audit_log.find({
        "$or": [
            {"ip": "testclient"},
            {"metadata.ip": "testclient"},
            {"details.ip": "testclient"},
        ]
    }))

    # 3. Empty conversations created on 2026-10-31 or 2026-11-01
    all_convs = list(db.conversations.find({}))
    empty_convs = []
    for c in all_convs:
        cid_str = str(c["_id"])
        msg_count = db.messages.count_documents({"conversation_id": cid_str})
        if msg_count == 0:
            msg_count = db.messages.count_documents({"conversation_id": c["_id"]})
        
        created = c.get("created_at")
        dt_str = created.isoformat() if hasattr(created, "isoformat") else str(created)
        if ("2026-10-31" in dt_str or "2026-11-01" in dt_str) and msg_count == 0:
            empty_convs.append(c)

    return test_users, test_audits, empty_convs


def main():
    parser = argparse.ArgumentParser(description="Find or remove leftover automated test records in MongoDB.")
    parser.add_argument("--apply", action="store_true", help="Execute deletion of listed records (default: dry run)")
    args = parser.parse_args()

    db = init_mongodb()
    if db is None:
        print("[ERROR] Cannot connect to MongoDB. Check MONGODB_URI in backend/.env", file=sys.stderr)
        return 1

    test_users, test_audits, empty_convs = find_test_records(db)

    print("=" * 70)
    print("LEFTOVER TEST RECORDS AUDIT")
    print("=" * 70)
    print(f"Mode: {'APPLY (DELETING RECORDS)' if args.apply else 'DRY RUN (NO CHANGES)'}")
    print("-" * 70)

    print(f"\n1. Test Users Identified ({len(test_users)}):")
    for u in test_users:
        print(f"  - ID: {u['_id']} | Email: {u.get('email')} | Name: {u.get('name')} | Created: {u.get('created_at')}")

    print(f"\n2. Test Audit Entries Identified ({len(test_audits)}):")
    for a in test_audits:
        ip = a.get("ip") or a.get("metadata", {}).get("ip") or a.get("details", {}).get("ip")
        print(f"  - ID: {a['_id']} | Action: {a.get('action')} | IP: {ip} | Timestamp: {a.get('timestamp')}")

    print(f"\n3. Empty Test Conversations ({len(empty_convs)}):")
    for c in empty_convs:
        print(f"  - ID: {c['_id']} | Title: {c.get('title')} | Created: {c.get('created_at')}")

    total_records = len(test_users) + len(test_audits) + len(empty_convs)
    print("\n" + "-" * 70)
    print(f"Total test records identified: {total_records}")

    if not args.apply:
        print("\n[DRY RUN] No records were deleted.")
        print("To delete only the listed IDs after owner review, run:")
        print("  python backend/scripts/remove_test_records.py --apply")
        print("=" * 70)
        return 0

    # Apply deletion only for listed IDs
    user_ids = [u["_id"] for u in test_users]
    audit_ids = [a["_id"] for a in test_audits]
    conv_ids = [c["_id"] for c in empty_convs]

    deleted_users = 0
    if user_ids:
        res = db.users.delete_many({"_id": {"$in": user_ids}})
        deleted_users = res.deleted_count

    deleted_audits = 0
    if audit_ids:
        res = db.audit_log.delete_many({"_id": {"$in": audit_ids}})
        deleted_audits = res.deleted_count

    deleted_convs = 0
    if conv_ids:
        res = db.conversations.delete_many({"_id": {"$in": conv_ids}})
        deleted_convs = res.deleted_count

    print(f"\n[APPLY COMPLETE] Deleted:")
    print(f"  - Users: {deleted_users}")
    print(f"  - Audit entries: {deleted_audits}")
    print(f"  - Conversations: {deleted_convs}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
