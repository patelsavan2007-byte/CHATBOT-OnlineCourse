"""
sync_website.py  –  Fetch latest content from charusat.online and update the
knowledge base md files.  Designed to run in CI (GitHub Actions) or locally.

Strategy
--------
1. Scrape charusat.online into a STAGING folder.
2. For each scraped file, compare with the live KB file using a diff ratio.
3. Only overwrite a KB file when:
   - it does not exist yet, OR
   - the scraped content changed by more than MIN_DIFF_RATIO (default 5 %)
4. Never overwrite files listed in PROTECTED_FILES (manually curated content).
5. Exit 0 always – network failures are logged, not fatal.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import difflib
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────────
BACKEND = Path(__file__).resolve().parent.parent          # …/backend
KB_DIR  = BACKEND / "knowledge_base"
STAGE   = BACKEND / "_stage_scraped"                      # temporary staging dir

# Minimum fraction of changed lines before we overwrite a KB file (5 %)
MIN_DIFF_RATIO: float = float(os.environ.get("MIN_DIFF_RATIO", "0.05"))

# These files were hand-crafted; the scraper must NEVER overwrite them
PROTECTED_FILES = {
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
}

# ── helpers ────────────────────────────────────────────────────────────────────

def _diff_ratio(old: str, new: str) -> float:
    """Return fraction of lines that differ between old and new text."""
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    return 1.0 - matcher.ratio()


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


# ── scrape ─────────────────────────────────────────────────────────────────────

def scrape_to_staging() -> list[Path]:
    """Run the existing scraper into STAGE; return list of files written."""
    # Clean staging dir
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    sys.path.insert(0, str(BACKEND))
    try:
        from app.scraper import crawl_internal_pages
    except ImportError as exc:
        print(f"[sync] ERROR: Cannot import scraper: {exc}")
        return []

    print(f"[sync] Scraping charusat.online → {STAGE}")
    try:
        files = crawl_internal_pages(
            start_url="https://charusat.online/",
            max_pages=40,
            output_dir=STAGE,
            use_playwright=False,
        )
        print(f"[sync] Scraped {len(files)} pages")
        return files or []
    except Exception as exc:
        print(f"[sync] WARNING: Scraping failed: {exc}")
        return []


# ── merge ──────────────────────────────────────────────────────────────────────

def merge_to_kb(staged_files: list[Path]) -> list[str]:
    """
    Copy changed staged files into KB_DIR, skipping protected files.
    Returns list of KB-relative paths that were updated.
    """
    updated: list[str] = []

    for staged_path in staged_files:
        # Compute relative path inside STAGE, use same relative path in KB
        try:
            rel = staged_path.relative_to(STAGE)
        except ValueError:
            continue

        # Flatten programs/ sub-paths into KB root to avoid duplicates
        # e.g.  programs/online_bca.md  →  online_bca_comprehensive.md (existing)
        # We leave programs/ files in staging; we only merge top-level ones.
        parts = rel.parts
        if len(parts) > 1 and parts[0] == "programs":
            print(f"[sync] SKIP  {rel} (programs/ sub-path – not merged into KB root)")
            continue

        filename = rel.name

        # Protect hand-crafted files
        if filename in PROTECTED_FILES:
            print(f"[sync] SKIP  {filename} (protected)")
            continue

        kb_target = KB_DIR / rel

        try:
            new_text = staged_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            print(f"[sync] ERROR reading {staged_path}: {exc}")
            continue

        # Compare with existing
        if kb_target.exists():
            old_text = kb_target.read_text(encoding="utf-8", errors="replace")
            ratio = _diff_ratio(old_text, new_text)
            if ratio < MIN_DIFF_RATIO:
                print(f"[sync] SKIP  {rel} (diff {ratio:.1%} < {MIN_DIFF_RATIO:.0%})")
                continue
            print(f"[sync] UPDATE {rel} (diff {ratio:.1%})")
        else:
            print(f"[sync] NEW   {rel}")

        kb_target.parent.mkdir(parents=True, exist_ok=True)
        kb_target.write_text(new_text, encoding="utf-8")
        updated.append(str(rel))

    return updated


# ── rebuild ────────────────────────────────────────────────────────────────────

def rebuild_vector_db() -> None:
    print("[sync] Rebuilding vector DB...")
    import subprocess
    python = sys.executable
    result = subprocess.run(
        [python, "-X", "utf8", "-I",
         str(BACKEND / "rebuild_vectordb.py")],
        cwd=str(BACKEND),
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"[sync] ERROR: rebuild_vectordb.py exited {result.returncode}")
        sys.exit(result.returncode)


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("[sync] === CHARUSAT Online KB Sync ===")
    staged = scrape_to_staging()

    if not staged:
        print("[sync] No pages scraped – nothing to update. Exiting.")
        # Still rebuild in case this is first run
        if any(KB_DIR.glob("*.md")):
            print("[sync] KB has files; skipping rebuild since nothing changed.")
        return

    updated = merge_to_kb(staged)
    print(f"[sync] Updated {len(updated)} KB file(s): {updated}")

    # Cleanup staging
    shutil.rmtree(STAGE, ignore_errors=True)

    if updated:
        rebuild_vector_db()
        print("[sync] Done – KB and vector DB are up to date.")
    else:
        print("[sync] No KB files changed – vector DB unchanged.")


if __name__ == "__main__":
    main()
