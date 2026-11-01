"""Knowledge Base Manager for CCOE CHARUSAT.

Handles:
- Upload file validation (file size, magic bytes, zip bomb protection, encryption check, page limits)
- Document conversion (PDF with PyMuPDF, DOCX with python-docx, MD/TXT)
- Unicode text cleaning (zero-width characters, odd whitespace, em dashes, Hindi/Gujarati preservation)
- Running header/footer stripping and hyphenation repair
- Temporary 1-hour draft storage
- GitHub API publishing (Contents API with 409 retry, Actions workflow dispatch)
- Path traversal guards and slug generation
- Live status derivation across vector store and GitHub Actions
"""
from __future__ import annotations

import asyncio
import base64
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from app import config
from app.utils import logger

# Directories
UPLOADS_DIR = config.KNOWLEDGE_BASE_DIR / "uploads"
UPLOADS_ORIGINALS_DIR = UPLOADS_DIR / "originals"

# Limits
MAX_UPLOAD_BYTES = 10 * 1024 * 1024       # 10 MB
MAX_DOCX_UNCOMPRESSED = 50 * 1024 * 1024  # 50 MB
MAX_DOCX_ENTRIES = 500
MAX_PDF_PAGES = 300
CONVERSION_TIMEOUT_SECONDS = 30
DRAFT_TTL_SECONDS = 3600                  # 1 hour

# In-memory drafts store: draft_id -> dict
_KB_DRAFTS: Dict[str, Dict[str, Any]] = {}


def ensure_upload_dirs() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Text & Unicode Normalization
# ---------------------------------------------------------------------------

_ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200d\ufeff]")
_ODD_SPACES_RE = re.compile(r"[\u00a0\u2000-\u200a\u202f\u205f]")
_HYPHENATION_RE = re.compile(r"(\b[a-zA-Z]+)-\s*\n\s*([a-zA-Z]+\b)")


def clean_unicode_text(text: str) -> str:
    """Clean text adhering to standing rules:

    - Delete zero-width characters (U+200B-200D, U+FEFF).
    - Normalize odd/non-breaking spaces to standard space U+0020.
    - Remove em dashes (U+2014) replacing with ' - '.
    - Preserve Indic scripts (Gujarati U+0A80-0AFF, Hindi/Devanagari U+0900-097F).
    """
    if not text:
        return ""
    # Strip zero-width characters
    cleaned = _ZERO_WIDTH_RE.sub("", text)
    # Normalize odd whitespace
    cleaned = _ODD_SPACES_RE.sub(" ", cleaned)
    # Replace em dashes with standard hyphen-space
    cleaned = cleaned.replace("\u2014", " - ")
    # Fix hyphenated words split over line breaks
    cleaned = _HYPHENATION_RE.sub(r"\1\2", cleaned)
    # Normalize excessive carriage returns
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    return cleaned


def estimate_chunks(markdown_text: str) -> int:
    """Estimate chunk count using character budget."""
    if not markdown_text or not markdown_text.strip():
        return 0
    step = max(100, config.CHUNK_SIZE - config.CHUNK_OVERLAP)
    return max(1, math.ceil(len(markdown_text.strip()) / step))


# ---------------------------------------------------------------------------
# Slug Generation & Path Traversal Guards
# ---------------------------------------------------------------------------

def generate_safe_slug(title: str, existing_slugs: Optional[List[str]] = None) -> str:
    """Generate a clean, filesystem-safe ASCII slug (max 60 characters)."""
    # Lowercase, replace non-alphanumeric with hyphen
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    if not slug:
        slug = f"doc-{uuid.uuid4().hex[:8]}"
    slug = slug[:60].rstrip("-")

    if existing_slugs and slug in existing_slugs:
        suffix = uuid.uuid4().hex[:6]
        slug = f"{slug[:53]}-{suffix}"

    return slug


def validate_safe_slug(slug: str) -> str:
    """Ensure slug contains only valid characters and has no path traversal components."""
    clean_slug = slug.strip()
    if not re.match(r"^[a-z0-9][a-z0-9-]{0,59}$", clean_slug):
        raise HTTPException(status_code=400, detail="Invalid document slug format")
    if ".." in clean_slug or "/" in clean_slug or "\\" in clean_slug or "\0" in clean_slug:
        raise HTTPException(status_code=400, detail="Path traversal detected in slug")

    target_path = (UPLOADS_DIR / f"{clean_slug}.md").resolve()
    uploads_resolved = UPLOADS_DIR.resolve()
    try:
        target_path.relative_to(uploads_resolved)
    except ValueError:
        raise HTTPException(status_code=400, detail="Target path is outside uploads directory")

    return clean_slug


# ---------------------------------------------------------------------------
# File Validation & Magic Bytes
# ---------------------------------------------------------------------------

def validate_uploaded_file(filename: str, file_bytes: bytes) -> str:
    """Validate file size, extension, and magic bytes.

    Returns normalized file extension ('pdf', 'docx', 'md', 'txt').
    """
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes)")

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum upload size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )

    # Check extension
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in ("pdf", "docx", "md", "txt"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Supported formats: PDF, DOCX, MD, TXT.",
        )

    # Magic byte verification
    if ext == "pdf":
        if not file_bytes.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="File content does not match PDF extension (invalid header)")
    elif ext == "docx":
        if not file_bytes.startswith(b"PK\x03\x04"):
            raise HTTPException(status_code=400, detail="File content does not match DOCX extension (not a valid zip archive)")
        # Inspect zip contents for zip bomb and word/document.xml
        try:
            import io
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                names = z.namelist()
                if len(names) > MAX_DOCX_ENTRIES:
                    raise HTTPException(status_code=400, detail="DOCX archive exceeds safe entry limit (potential zip bomb)")
                total_uncompressed = sum(info.file_size for info in z.infolist())
                if total_uncompressed > MAX_DOCX_UNCOMPRESSED:
                    raise HTTPException(status_code=400, detail="DOCX uncompressed size exceeds 50 MB limit")
                if "word/document.xml" not in names:
                    raise HTTPException(status_code=400, detail="Invalid DOCX package (word/document.xml missing)")
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Corrupted DOCX archive")
    elif ext in ("md", "txt"):
        if b"\x00" in file_bytes[:1024]:
            raise HTTPException(status_code=400, detail="Binary content detected in text file")
        try:
            file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                file_bytes.decode("latin-1")
            except Exception:
                raise HTTPException(status_code=400, detail="Text file must be valid UTF-8 or ASCII")

    return ext


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------

def _convert_pdf_sync(file_bytes: bytes) -> Tuple[str, List[str], int, bool]:
    """Convert PDF to Markdown with heading detection, table parsing,

    and running header/footer removal using PyMuPDF.
    Returns (markdown, warnings, page_count, can_publish).
    """
    import fitz  # PyMuPDF

    warnings: List[str] = []
    can_publish = True

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to open PDF: {exc}")

    if getattr(doc, "is_encrypted", False) or getattr(doc, "needs_pass", False):
        raise HTTPException(status_code=400, detail="Encrypted PDFs are not supported")

    page_count = len(doc)
    if page_count > MAX_PDF_PAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Document exceeds maximum page limit of {MAX_PDF_PAGES} pages (found {page_count})",
        )

    # 1. Analyze font size distribution to find body font size
    font_sizes: List[float] = []
    for page in doc:
        blocks = page.get_text("dict").get("blocks", [])
        for b in blocks:
            if "lines" in b:
                for line in b["lines"]:
                    for span in line.get("spans", []):
                        sz = round(span.get("size", 10.0), 1)
                        if sz > 0:
                            font_sizes.append(sz)

    base_font_size = 11.0
    if font_sizes:
        # Most frequent font size
        from collections import Counter
        base_font_size = Counter(font_sizes).most_common(1)[0][0]

    # 2. Detect repeated running headers and footers across pages
    top_candidates: Dict[str, int] = {}
    bot_candidates: Dict[str, int] = {}
    for page in doc:
        h = page.rect.height
        text_dict = page.get_text("dict")
        for b in text_dict.get("blocks", []):
            if "lines" in b:
                line_texts = []
                for line in b["lines"]:
                    lt = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
                    if lt:
                        line_texts.append(lt)
                block_str = " ".join(line_texts).strip()
                if block_str and len(block_str) < 120:
                    y0, y1 = b["bbox"][1], b["bbox"][3]
                    if y0 < 55:
                        top_candidates[block_str] = top_candidates.get(block_str, 0) + 1
                    elif y1 > (h - 55):
                        bot_candidates[block_str] = bot_candidates.get(block_str, 0) + 1

    repeated_headers = {txt for txt, cnt in top_candidates.items() if cnt >= max(2, int(page_count * 0.6))}
    repeated_footers = {txt for txt, cnt in bot_candidates.items() if cnt >= max(2, int(page_count * 0.6))}

    # 3. Extract content page by page
    md_pages: List[str] = []
    total_text_chars = 0

    for page_idx, page in enumerate(doc):
        page_lines: List[str] = []
        h = page.rect.height

        # A. Extract tables via PyMuPDF table finder if available
        tables_data = []
        table_rects = []
        if hasattr(page, "find_tables"):
            try:
                tabs = page.find_tables()
                for tab in tabs:
                    table_rects.append(tab.bbox)
                    df = tab.extract()
                    if df and len(df) > 1:
                        # Convert to markdown table
                        headers = [str(c or "").strip().replace("|", "/") for c in df[0]]
                        sep = ["---"] * len(headers)
                        rows = [
                            [str(c or "").strip().replace("|", "/") for c in row]
                            for row in df[1:]
                        ]
                        t_md = (
                            f"\n| {' | '.join(headers)} |\n"
                            f"| {' | '.join(sep)} |\n"
                            + "\n".join(f"| {' | '.join(r)} |" for r in rows)
                            + "\n"
                        )
                        tables_data.append((tab.bbox, t_md))
            except Exception:
                pass

        # B. Extract text blocks outside table rects
        blocks = page.get_text("dict").get("blocks", [])
        for b in blocks:
            if "lines" not in b:
                continue

            bx0, by0, bx1, by1 = b["bbox"]
            # Check if block falls inside any table bbox
            in_table = any(
                (bx0 >= tr[0] - 2 and by0 >= tr[1] - 2 and bx1 <= tr[2] + 2 and by1 <= tr[3] + 2)
                for tr in table_rects
            )
            if in_table:
                continue

            block_text = ""
            max_span_size = 0.0
            for line in b["lines"]:
                for span in line.get("spans", []):
                    stext = span.get("text", "")
                    block_text += stext
                    max_span_size = max(max_span_size, span.get("size", base_font_size))
                block_text += "\n"

            cleaned_b = block_text.strip()
            if not cleaned_b:
                continue

            # Check if repeated header or footer
            if by0 < 55 and cleaned_b in repeated_headers:
                continue
            if by1 > (h - 55) and (cleaned_b in repeated_footers or re.match(r"^Page \d+( of \d+)?$", cleaned_b, re.IGNORECASE)):
                continue

            total_text_chars += len(cleaned_b)

            # Determine if heading
            if max_span_size >= base_font_size * 1.5 and len(cleaned_b) < 120 and "\n" not in cleaned_b:
                page_lines.append(f"\n## {cleaned_b}\n")
            elif max_span_size >= base_font_size * 1.25 and len(cleaned_b) < 140 and "\n" not in cleaned_b:
                page_lines.append(f"\n### {cleaned_b}\n")
            else:
                page_lines.append(cleaned_b)

        # Append tables
        for _, t_md in tables_data:
            page_lines.append(t_md)
            total_text_chars += len(t_md)

        if page_lines:
            md_pages.append("\n\n".join(page_lines))

    # Scanned PDF check
    if total_text_chars < 40:
        warnings.append("No text found. Scanned files are not supported yet.")
        can_publish = False

    raw_markdown = "\n\n".join(md_pages)
    final_markdown = clean_unicode_text(raw_markdown)
    return final_markdown, warnings, page_count, can_publish


def _convert_docx_sync(file_bytes: bytes) -> Tuple[str, List[str], int, bool]:
    """Convert DOCX to Markdown with paragraphs, headings and tables."""
    import docx
    import io

    warnings: List[str] = []
    can_publish = True

    try:
        doc = docx.Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read DOCX document: {exc}")

    lines: List[str] = []
    total_chars = 0

    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue
        total_chars += len(txt)
        style_name = (p.style.name if p.style else "").lower()

        if "heading 1" in style_name:
            lines.append(f"\n# {txt}\n")
        elif "heading 2" in style_name:
            lines.append(f"\n## {txt}\n")
        elif "heading 3" in style_name:
            lines.append(f"\n### {txt}\n")
        elif len(txt) < 80 and any(run.bold for run in p.runs if run.text.strip()):
            lines.append(f"\n### {txt}\n")
        else:
            lines.append(txt)

    # Tables
    for table in doc.tables:
        table_rows = []
        for row in table.rows:
            table_rows.append([cell.text.strip().replace("\n", " ").replace("|", "/") for cell in row.cells])
        if table_rows and len(table_rows) > 1:
            headers = table_rows[0]
            sep = ["---"] * len(headers)
            t_md = (
                f"\n| {' | '.join(headers)} |\n"
                f"| {' | '.join(sep)} |\n"
                + "\n".join(f"| {' | '.join(r)} |" for r in table_rows[1:])
                + "\n"
            )
            lines.append(t_md)
            total_chars += len(t_md)

    if total_chars < 20:
        warnings.append("Document appears empty or contains no readable text.")
        can_publish = False

    final_markdown = clean_unicode_text("\n\n".join(lines))
    return final_markdown, warnings, 1, can_publish


def _convert_text_sync(file_bytes: bytes) -> Tuple[str, List[str], int, bool]:
    """Convert plain text or Markdown to standardized clean Markdown."""
    warnings: List[str] = []
    can_publish = True
    try:
        raw_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = file_bytes.decode("latin-1", errors="replace")

    clean_text = clean_unicode_text(raw_text)
    if len(clean_text.strip()) < 10:
        warnings.append("Text file contains little or no content.")
        can_publish = False

    return clean_text, warnings, 1, can_publish


async def convert_file_to_markdown(
    filename: str,
    file_bytes: bytes,
) -> Tuple[str, List[str], int, bool]:
    """Asynchronously convert uploaded file to markdown with 30-second timeout."""
    ext = validate_uploaded_file(filename, file_bytes)

    loop = asyncio.get_running_loop()

    if ext == "pdf":
        target_fn = _convert_pdf_sync
    elif ext == "docx":
        target_fn = _convert_docx_sync
    else:
        target_fn = _convert_text_sync

    try:
        markdown, warnings, pages, can_publish = await asyncio.wait_for(
            loop.run_in_executor(None, target_fn, file_bytes),
            timeout=CONVERSION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="File conversion timed out (exceeded 30 seconds limit)")

    return markdown, warnings, pages, can_publish


# ---------------------------------------------------------------------------
# Draft Management
# ---------------------------------------------------------------------------

def create_draft(
    title: str,
    filename: str,
    markdown: str,
    warnings: List[str],
    page_count: int,
    can_publish: bool,
    file_bytes: bytes,
    programme: str = "GENERAL",
) -> Dict[str, Any]:
    """Store converted file in memory draft store for up to 1 hour."""
    now = time.time()
    # Cleanup expired drafts
    expired = [k for k, v in _KB_DRAFTS.items() if (now - v.get("created_at", 0)) > DRAFT_TTL_SECONDS]
    for k in expired:
        _KB_DRAFTS.pop(k, None)

    draft_id = f"draft_{uuid.uuid4().hex[:12]}"
    chunk_est = estimate_chunks(markdown)

    draft = {
        "draft_id": draft_id,
        "title": title or Path(filename).stem,
        "filename": filename,
        "extension": Path(filename).suffix.lower().lstrip("."),
        "markdown": markdown,
        "warnings": warnings,
        "page_count": page_count,
        "chunk_estimate": chunk_est,
        "can_publish": can_publish,
        "programme": programme.upper() if programme else "GENERAL",
        "source_note": "",
        "replaces_file": None,
        "original_bytes": file_bytes if len(file_bytes) <= 5 * 1024 * 1024 else None,
        "created_at": now,
    }
    _KB_DRAFTS[draft_id] = draft
    return draft


def get_draft(draft_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve draft by ID if still active."""
    draft = _KB_DRAFTS.get(draft_id)
    if not draft:
        return None
    if (time.time() - draft.get("created_at", 0)) > DRAFT_TTL_SECONDS:
        _KB_DRAFTS.pop(draft_id, None)
        return None
    return draft


def update_draft(draft_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update fields in an existing draft."""
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found or expired")

    allowed_fields = {"title", "markdown", "programme", "source_note", "replaces_file"}
    for k, v in updates.items():
        if k in allowed_fields and v is not None:
            if k == "markdown":
                draft[k] = clean_unicode_text(str(v))
                draft["chunk_estimate"] = estimate_chunks(draft[k])
            elif k == "programme":
                draft[k] = str(v).upper()
            else:
                draft[k] = v

    return draft


# ---------------------------------------------------------------------------
# GitHub Client
# ---------------------------------------------------------------------------

class GitHubClient:
    """Client for GitHub Contents API and Actions Workflow Dispatches."""

    def __init__(self):
        self.repo = os.getenv("GITHUB_REPO", "").strip()
        self.branch = os.getenv("GITHUB_BRANCH", "main").strip()
        self.token = os.getenv("GITHUB_TOKEN", "").strip()
        self.workflow_file = os.getenv("GITHUB_WORKFLOW_FILE", "sync-knowledge-base.yml").strip()

    def is_configured(self) -> Tuple[bool, List[str]]:
        missing = []
        if not self.repo:
            missing.append("GITHUB_REPO")
        if not self.token:
            missing.append("GITHUB_TOKEN")
        if not self.workflow_file:
            missing.append("GITHUB_WORKFLOW_FILE")
        return (len(missing) == 0, missing)

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "CHARUSAT-CCOE-KB-Manager/1.0",
        }

    def _request(self, method: str, url: str, data: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
        req_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=req_data, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                status_code = resp.status
                body = resp.read().decode("utf-8")
                return status_code, json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
            except Exception:
                err_json = {"message": err_body}
            return exc.code, err_json

    def get_file_sha(self, path_in_repo: str) -> Optional[str]:
        """Fetch current SHA of a file in the repository."""
        url = f"https://api.github.com/repos/{self.repo}/contents/{path_in_repo}?ref={self.branch}"
        code, data = self._request("GET", url)
        if code == 200 and isinstance(data, dict):
            return data.get("sha")
        return None

    def commit_file(
        self,
        path_in_repo: str,
        content_bytes: bytes,
        commit_message: str,
    ) -> bool:
        """Commit or update a file via GitHub Contents API with 409 conflict retry."""
        url = f"https://api.github.com/repos/{self.repo}/contents/{path_in_repo}"
        content_b64 = base64.b64encode(content_bytes).decode("ascii")

        sha = self.get_file_sha(path_in_repo)
        payload: Dict[str, Any] = {
            "message": commit_message,
            "content": content_b64,
            "branch": self.branch,
        }
        if sha:
            payload["sha"] = sha

        code, resp = self._request("PUT", url, payload)
        if code in (200, 201):
            return True

        if code == 409:
            # Conflict: fetch newest SHA and retry once
            logger.warning("GitHub 409 Conflict committing %s. Retrying once...", path_in_repo)
            time.sleep(0.5)
            sha = self.get_file_sha(path_in_repo)
            if sha:
                payload["sha"] = sha
            else:
                payload.pop("sha", None)
            code, resp = self._request("PUT", url, payload)
            if code in (200, 201):
                return True

        logger.error("GitHub commit failed for %s: code=%d resp=%s", path_in_repo, code, resp)
        raise HTTPException(
            status_code=502,
            detail=f"GitHub Contents API error ({code}): {resp.get('message', 'Failed to commit')}",
        )

    def delete_file(self, path_in_repo: str, commit_message: str) -> bool:
        """Delete a file from GitHub repository."""
        sha = self.get_file_sha(path_in_repo)
        if not sha:
            # File does not exist on GitHub
            return True

        url = f"https://api.github.com/repos/{self.repo}/contents/{path_in_repo}"
        payload = {
            "message": commit_message,
            "sha": sha,
            "branch": self.branch,
        }
        code, resp = self._request("DELETE", url, payload)
        if code in (200, 204):
            return True

        logger.error("GitHub delete failed for %s: code=%d resp=%s", path_in_repo, code, resp)
        raise HTTPException(
            status_code=502,
            detail=f"GitHub Contents API error ({code}): {resp.get('message', 'Failed to delete')}",
        )

    def trigger_workflow(self, force_rebuild: bool = False) -> bool:
        """Trigger workflow_dispatch for sync-knowledge-base.yml."""
        url = (
            f"https://api.github.com/repos/{self.repo}/actions/workflows/"
            f"{self.workflow_file}/dispatches"
        )
        payload = {
            "ref": self.branch,
            "inputs": {
                "force_rebuild": "true" if force_rebuild else "false",
            },
        }
        code, resp = self._request("POST", url, payload)
        if code in (200, 204):
            return True

        logger.error("GitHub workflow dispatch failed: code=%d resp=%s", code, resp)
        raise HTTPException(
            status_code=502,
            detail=f"GitHub Actions dispatch error ({code}): {resp.get('message', 'Failed to trigger workflow')}",
        )

    def get_latest_workflow_run(self) -> Optional[Dict[str, Any]]:
        """Fetch the latest workflow run status."""
        url = (
            f"https://api.github.com/repos/{self.repo}/actions/workflows/"
            f"{self.workflow_file}/runs?per_page=1"
        )
        code, data = self._request("GET", url)
        if code == 200 and isinstance(data, dict):
            runs = data.get("workflow_runs", [])
            if runs:
                run = runs[0]
                return {
                    "id": run.get("id"),
                    "status": run.get("status"),           # "queued", "in_progress", "completed"
                    "conclusion": run.get("conclusion"),   # "success", "failure", etc.
                    "updated_at": run.get("updated_at"),
                    "html_url": run.get("html_url"),
                    "trigger": run.get("event"),
                }
        return None


# ---------------------------------------------------------------------------
# Document Status & Inventory
# ---------------------------------------------------------------------------

def get_kb_inventory(
    vector_store: Any,
    github_client: GitHubClient,
) -> Dict[str, Any]:
    """Compile inventory of all KB documents and automation status."""
    ensure_upload_dirs()

    # 1. Check automation heartbeat or GitHub Actions
    gh_configured, missing_vars = github_client.is_configured()
    automation_info: Dict[str, Any] = {
        "configured": gh_configured,
        "missing_env_vars": missing_vars,
        "last_run": None,
        "status": "idle",
        "result": None,
        "trigger": None,
        "run_url": None,
    }

    latest_run = None
    if gh_configured:
        try:
            latest_run = github_client.get_latest_workflow_run()
            if latest_run:
                automation_info["last_run"] = latest_run.get("updated_at")
                automation_info["status"] = latest_run.get("status")
                automation_info["result"] = latest_run.get("conclusion")
                automation_info["trigger"] = latest_run.get("trigger")
                automation_info["run_url"] = latest_run.get("html_url")
        except Exception as exc:
            logger.warning("Failed to query GitHub workflow runs: %s", exc)

    # Fallback to backend/last_sync.json if not found from GitHub
    if not automation_info["last_run"]:
        last_sync_path = config.BASE_DIR / "last_sync.json"
        if last_sync_path.exists():
            try:
                with open(last_sync_path, "r", encoding="utf-8") as f:
                    sync_data = json.load(f)
                    automation_info["last_run"] = sync_data.get("last_run_utc")
                    automation_info["trigger"] = sync_data.get("trigger")
                    automation_info["run_url"] = sync_data.get("run_url")
                    automation_info["result"] = "success"
            except Exception:
                pass

    # 2. Vector store chunks tally by source
    chunk_counts_by_source: Dict[str, int] = {}
    total_chunks = 0
    if vector_store is not None:
        try:
            coll = getattr(vector_store, "_collection", None)
            if coll is not None:
                total_chunks = coll.count()
                all_docs = coll.get(include=["metadatas"])
                for meta in all_docs.get("metadatas", []):
                    src = (meta or {}).get("source") or ""
                    if src:
                        chunk_counts_by_source[src] = chunk_counts_by_source.get(src, 0) + 1
        except Exception as exc:
            logger.warning("Failed to tally vector store chunks: %s", exc)

    # 3. Scan all markdown files in knowledge_base
    docs: List[Dict[str, Any]] = []
    kb_path = config.KNOWLEDGE_BASE_DIR

    is_rebuilding = automation_info.get("status") in ("queued", "in_progress")

    for fpath in kb_path.rglob("*.md"):
        # Ignore backups, superseded, hidden
        parts = fpath.parts
        if any(p.startswith(".") or p in ("_backup", "superseded", "__pycache__") for p in parts):
            continue

        rel = fpath.relative_to(kb_path).as_posix()
        stat = fpath.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

        # Parse front matter
        title = fpath.stem
        programme = "General"
        source_type = "Website"
        kind = "scraped"
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
            if content.startswith("---"):
                end_fm = content.find("---", 3)
                if end_fm != -1:
                    fm_text = content[3:end_fm]
                    for line in fm_text.splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            k, v = k.strip().lower(), v.strip()
                            if k == "title" and v:
                                title = v
                            elif k == "programme" and v:
                                programme = v.upper()
                            elif k == "kind" and v:
                                kind = v
        except Exception:
            pass

        # Source type determination
        if rel.startswith("uploads/"):
            source_type = "Upload"
        elif rel in ("placement_recruiters.md", "contact_directory.md"):
            source_type = "Manual"
        else:
            source_type = "Website"

        # Chunks in vector store
        chunks = chunk_counts_by_source.get(rel, 0)
        # Also try matching filename if not found by relative path
        if chunks == 0:
            chunks = chunk_counts_by_source.get(fpath.name, 0)

        # Status determination:
        # Rebuilding: workflow run in progress
        # Live: chunks present in index
        # Saved to repository: committed/saved but not indexed
        # Failed: latest workflow run failed
        if is_rebuilding and chunks == 0:
            doc_status = "Rebuilding"
        elif chunks > 0:
            doc_status = "Live"
        elif automation_info.get("result") == "failure":
            doc_status = "Failed"
        else:
            doc_status = "Saved to repository"

        slug = fpath.stem

        docs.append({
            "slug": slug,
            "filename": fpath.name,
            "rel_path": rel,
            "title": title,
            "source_type": source_type,
            "programme": programme,
            "kind": kind,
            "chunks": chunks,
            "last_modified": mtime,
            "status": doc_status,
            "can_delete": source_type == "Upload",
            "can_edit": source_type == "Upload",
        })

    docs.sort(key=lambda d: (d["source_type"] != "Upload", d["rel_path"]))

    return {
        "automation": automation_info,
        "index": {
            "total_chunks": total_chunks,
            "total_documents": len(docs),
        },
        "documents": docs,
    }
