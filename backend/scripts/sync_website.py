"""
sync_website.py  –  Daily scrape of charusat.online → update KB markdown files
                    → rebuild ChromaDB vector store (only when KB changed).

Designed for GitHub Actions (runs on `main` branch) and local use.

Pipeline
--------
1. Scrape charusat.online into a temporary STAGING folder.
2. For each scraped file compare with the live KB file using a diff ratio.
3. Overwrite a KB file only when:
   - it does not exist yet, OR
   - scraped content changed by more than MIN_DIFF_RATIO (default 5 %)
4. Never overwrite files listed in PROTECTED_FILES (manually-curated content).
5. If any KB file changed → rebuild ChromaDB.
6. Print a structured run report (also surfaced in GitHub Actions summary).
7. Exit 0 always – network failures are logged, not fatal.
"""
from __future__ import annotations

import difflib
import hashlib
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# ── paths ──────────────────────────────────────────────────────────────────────
BACKEND = Path(__file__).resolve().parent.parent          # …/backend
KB_DIR  = BACKEND / "knowledge_base"
STAGE   = BACKEND / "_stage_scraped"                      # temporary staging dir
LOG_DIR = BACKEND / "_sync_logs"

# ── tunables ──────────────────────────────────────────────────────────────────
# Minimum fraction of changed lines before we overwrite a KB file (5 %)
MIN_DIFF_RATIO: float = float(os.environ.get("MIN_DIFF_RATIO", "0.05"))

# Number of previous scraped snapshots to keep (0 = no backup)
MAX_BACKUPS: int = int(os.environ.get("KB_MAX_BACKUPS", "3"))

# ── protected files ────────────────────────────────────────────────────────────
# These files were hand-crafted; the scraper must NEVER overwrite them.
PROTECTED_FILES: frozenset[str] = frozenset({
    "admissions_guide.md",
    "admission_cancellation.md",
    "aicte_eoa_comprehensive.md",
    "bca_syllabus_2025_26.md",
    "mca_syllabus_2025_26.md",
    "ciqa.md",
    "contact_directory.md",
    "faculty.md",
    "feedback.md",
    "ppr_online_bba.md",
    "ppr_online_bca.md",
    "ppr_online_mba.md",
    "ppr_online_mca.md",
    "privacy-policy.md",
    "refund_policy.md",
    "terms-conditions.md",
    "ugc_public_notice.md",
})

# ── helpers ────────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(tag: str, msg: str, *, file=sys.stdout) -> None:
    print(f"[{_ts()}] [{tag}] {msg}", file=file, flush=True)


def _diff_ratio(old: str, new: str) -> float:
    """Return fraction of lines that differ between old and new text."""
    old_lines = old.splitlines()
    new_lines  = new.splitlines()
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    return 1.0 - matcher.ratio()


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _rotate_backups() -> None:
    """Keep at most MAX_BACKUPS snapshot folders inside KB_DIR/_backup/."""
    if MAX_BACKUPS <= 0:
        return
    backup_root = KB_DIR / "_backup"
    backup_root.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest  = backup_root / stamp
    # Copy current KB (only .md files, not sub-dirs like _backup)
    dest.mkdir()
    for md in KB_DIR.glob("*.md"):
        shutil.copy2(md, dest / md.name)
    _log("BACKUP", f"Snapshot saved to {dest.relative_to(BACKEND)}")
    # Prune old snapshots
    snapshots = sorted(backup_root.iterdir())
    while len(snapshots) > MAX_BACKUPS:
        old = snapshots.pop(0)
        shutil.rmtree(old, ignore_errors=True)
        _log("BACKUP", f"Pruned old snapshot {old.name}")


# ── scrape ─────────────────────────────────────────────────────────────────────

def scrape_to_staging() -> List[Path]:
    """Run the scraper into STAGE; return list of files written."""
    # Clean staging dir
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    sys.path.insert(0, str(BACKEND))
    try:
        from app.scraper import crawl_internal_pages
    except ImportError as exc:
        _log("ERROR", f"Cannot import scraper: {exc}", file=sys.stderr)
        return []

    _log("SCRAPE", f"Scraping charusat.online → {STAGE.relative_to(BACKEND)}")
    t0 = time.monotonic()
    try:
        files = crawl_internal_pages(
            start_url="https://charusat.online/",
            max_pages=40,
            output_dir=STAGE,
            use_playwright=False,
        )
        elapsed = time.monotonic() - t0
        _log("SCRAPE", f"Done – {len(files)} page(s) in {elapsed:.1f}s")
        return files or []
    except Exception as exc:
        _log("WARN", f"Scraping failed: {exc}", file=sys.stderr)
        return []


# ── merge ──────────────────────────────────────────────────────────────────────

def merge_to_kb(staged_files: List[Path]) -> Dict[str, str]:
    """
    Copy changed staged files into KB_DIR, skipping protected files.
    Returns dict of { kb_rel_path: "new" | "updated" | "skipped:protected"
                                   | "skipped:unchanged" }.
    """
    results: Dict[str, str] = {}

    for staged_path in staged_files:
        try:
            rel = staged_path.relative_to(STAGE)
        except ValueError:
            continue

        # Flatten programs/ sub-paths – we only merge top-level MD files
        parts = rel.parts
        if len(parts) > 1 and parts[0] == "programs":
            _log("SKIP", f"{rel}  (programs/ sub-path – not merged into KB root)")
            results[str(rel)] = "skipped:programs"
            continue

        filename = rel.name

        # Protect hand-crafted files
        if filename in PROTECTED_FILES:
            _log("SKIP", f"{filename}  (protected)")
            results[filename] = "skipped:protected"
            continue

        kb_target = KB_DIR / rel

        try:
            new_text = staged_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            _log("ERROR", f"Reading {staged_path}: {exc}", file=sys.stderr)
            continue

        # Compare with existing
        if kb_target.exists():
            old_text = kb_target.read_text(encoding="utf-8", errors="replace")
            ratio = _diff_ratio(old_text, new_text)
            if ratio < MIN_DIFF_RATIO:
                _log("SKIP", f"{rel}  (diff {ratio:.1%} < {MIN_DIFF_RATIO:.0%} threshold)")
                results[str(rel)] = "skipped:unchanged"
                continue
            _log("UPDATE", f"{rel}  (diff {ratio:.1%})")
            results[str(rel)] = f"updated:{ratio:.1%}"
        else:
            _log("NEW", str(rel))
            results[str(rel)] = "new"

        kb_target.parent.mkdir(parents=True, exist_ok=True)
        kb_target.write_text(new_text, encoding="utf-8")

    return results


# ── rebuild ────────────────────────────────────────────────────────────────────

def rebuild_vector_db() -> bool:
    """Rebuild ChromaDB. Returns True on success."""
    _log("REBUILD", "Starting vector DB rebuild...")
    t0 = time.monotonic()
    python = sys.executable
    result = subprocess.run(
        [python, "-X", "utf8", "-I", str(BACKEND / "rebuild_vectordb.py")],
        cwd=str(BACKEND),
        capture_output=False,
    )
    elapsed = time.monotonic() - t0
    if result.returncode != 0:
        _log("ERROR", f"rebuild_vectordb.py exited {result.returncode} after {elapsed:.1f}s",
             file=sys.stderr)
        return False
    _log("REBUILD", f"Vector DB rebuilt in {elapsed:.1f}s")
    return True


# ── report ─────────────────────────────────────────────────────────────────────

def _print_report(results: Dict[str, str], rebuild_ok: bool | None) -> None:
    """Print a human-readable sync report."""
    new_count      = sum(1 for v in results.values() if v == "new")
    updated_count  = sum(1 for v in results.values() if v.startswith("updated"))
    skipped_count  = sum(1 for v in results.values() if v.startswith("skipped"))

    print()
    print("=" * 60)
    print("  CHARUSAT Online KB Sync Report")
    print("=" * 60)
    print(f"  Timestamp (UTC) : {_ts()}")
    print(f"  Min diff ratio  : {MIN_DIFF_RATIO:.0%}")
    print()
    print(f"  Files new       : {new_count}")
    print(f"  Files updated   : {updated_count}")
    print(f"  Files skipped   : {skipped_count}")
    if rebuild_ok is True:
        print(f"  Vector DB       : rebuilt ✓")
    elif rebuild_ok is False:
        print(f"  Vector DB       : REBUILD FAILED ✗")
    else:
        print(f"  Vector DB       : not rebuilt (no KB changes)")
    print("=" * 60)

    if new_count or updated_count:
        print("\nChanged files:")
        for path, status in sorted(results.items()):
            if status not in ("skipped:protected", "skipped:programs", "skipped:unchanged"):
                print(f"  [{status}] {path}")
    print()


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    _log("SYNC", "=== CHARUSAT Online KB Daily Sync ===")
    _log("SYNC", f"KB directory  : {KB_DIR}")
    _log("SYNC", f"Min diff ratio: {MIN_DIFF_RATIO:.0%}")

    # Step 1 – scrape
    staged = scrape_to_staging()
    if not staged:
        _log("WARN", "No pages scraped – nothing to update.")
        _print_report({}, None)
        return

    # Step 2 – backup current KB before modifying
    _rotate_backups()

    # Step 3 – merge staged files into KB
    results = merge_to_kb(staged)

    # Cleanup staging dir
    shutil.rmtree(STAGE, ignore_errors=True)

    changed = [k for k, v in results.items()
               if v == "new" or v.startswith("updated")]
    _log("SYNC", f"{len(changed)} KB file(s) changed")

    # Step 4 – rebuild vector DB if anything changed
    rebuild_ok: bool | None = None
    if changed:
        rebuild_ok = rebuild_vector_db()
    else:
        _log("SYNC", "No KB files changed – skipping vector DB rebuild.")

    _print_report(results, rebuild_ok)

    # Exit non-zero if rebuild failed (so CI marks the run as failed)
    if rebuild_ok is False:
        sys.exit(1)


if __name__ == "__main__":
    main()
