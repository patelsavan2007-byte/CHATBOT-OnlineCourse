from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownTextSplitter,
    NLTKTextSplitter,
)

from app.config import CHUNK_OVERLAP, CHUNK_SIZE, KNOWLEDGE_BASE_DIR, VECTOR_DB_DIR
from app.scraper import crawl_internal_pages
from app.utils import logger, print_info, print_warning


def is_valid_chunk(text: str) -> bool:
    """Return False if chunk has no real meaningful text (<80 chars, <40 alnum chars, or empty table)."""
    clean = text.strip()
    if len(clean) < 80:
        return False
    # Check alphanumeric characters
    alnum = re.sub(r"[^a-zA-Z0-9]", "", clean)
    if len(alnum) < 40:
        return False
    # Check if empty table (lines starting and ending with |, but only spaces inside)
    table_lines = [l.strip() for l in clean.splitlines() if l.strip().startswith("|") and l.strip().endswith("|")]
    if table_lines and len(table_lines) == len([l for l in clean.splitlines() if l.strip()]):
        non_pipe = re.sub(r"[\|\s\-\:]+", "", clean)
        if len(non_pipe) < 20:
            return False
    return True


def deduplicate_chunks(chunks: List[Document]) -> List[Document]:
    """Remove exact and near-exact duplicates at ingestion time."""
    seen = {}
    deduped = []
    for c in chunks:
        norm = re.sub(r"\s+", " ", c.page_content.strip().lower())
        prog = c.metadata.get("program_name", "")
        key = (prog, norm[:250])
        if key in seen:
            continue
        seen[key] = True
        deduped.append(c)
    return deduped


class KnowledgeBaseIngester:
    # Files that must never be indexed into the vector store
    EXCLUDED_FILES = frozenset([
        "deep-research-report.md",
        "charusat_online_programs_knowledge_base.txt",
    ])
    def __init__(self) -> None:
        self.knowledge_dir = KNOWLEDGE_BASE_DIR
        self.vector_dir = VECTOR_DB_DIR
        self.manifest_path = self.vector_dir / "source_manifest.json"

    def _cleanup_source_files(self) -> None:
        if not self.knowledge_dir.exists():
            return

        for path in sorted(self.knowledge_dir.rglob("*"), reverse=True):
            if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()

    def refresh_sources(self) -> List[Path]:
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.vector_dir.mkdir(parents=True, exist_ok=True)

        self._cleanup_source_files()

        try:
            scraped_files = crawl_internal_pages(output_dir=self.knowledge_dir)
            if scraped_files:
                print_info(f"Scraped {len(scraped_files)} pages into the knowledge base.")
        except Exception as exc:  # pragma: no cover - network failures should not crash startup
            print_warning(f"Scraping skipped: {exc}")
            return []

        return scraped_files

    def get_source_files(self) -> List[Path]:
        if not self.knowledge_dir.exists():
            self.knowledge_dir.mkdir(parents=True, exist_ok=True)

        files = [
            path
            for path in self.knowledge_dir.rglob("*")
            if path.is_file() and path.suffix.lower() == ".md"
            and "__pycache__" not in path.parts
            and "vector_db" not in path.parts
            and path.name.lower() not in self.EXCLUDED_FILES
        ]
        return sorted(files)

    def _parse_markdown_metadata(self, content: str, path: Path) -> tuple[str, Dict[str, str]]:
        lines = content.splitlines()
        metadata: Dict[str, str] = {}
        body_lines: List[str] = []
        parsing_metadata = True

        for line in lines:
            stripped = line.strip()
            if parsing_metadata and not stripped:
                parsing_metadata = False
                continue

            if parsing_metadata and ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip().lower()] = value.strip()
                continue

            parsing_metadata = False
            body_lines.append(line)

        body = "\n".join(body_lines).strip()
        if not body:
            body = content

        return body, metadata

    def _parse_program_name(self, file_metadata: Dict[str, str], path: Path) -> str:
        from urllib.parse import urlparse
        stem = path.stem.lower()
        url = file_metadata.get("url", "").lower()
        url_path = urlparse(url).path.lower()

        # Per-programme files: online_<prog>.md, online_<prog>_comprehensive.md,
        # PPR_Online <PROG>.md etc. Cross-programme guides (admissions, exam,
        # AICTE, contact) intentionally get no programme tag.
        for prog in ("bca", "bba", "mba", "mca"):
            if (
                stem == f"online_{prog}"
                or stem.startswith(f"online_{prog}_")
                or stem.replace(" ", "_") == f"ppr_online_{prog}"
                or url_path.endswith(f"/programs/{prog}.html")
                or url_path.endswith(f"/programs/{prog}")
            ):
                return f"online_{prog}"
        return ""

    def load_documents(self) -> List[Document]:
        documents: List[Document] = []
        files = self.get_source_files()
        if not files:
            self.refresh_sources()
            files = self.get_source_files()

        if not files:
            raise ValueError("No Markdown files found in the knowledge base directory.")

        print_info(f"Loaded files: {', '.join(path.name for path in files)}")
        logger.info("Loaded files: %s", ", ".join(path.name for path in files))

        for path in files:
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"Corrupted file: {path.name}") from exc

            body, file_metadata = self._parse_markdown_metadata(content, path)

            # Allow files without URL metadata (manually created comprehensive files)
            url = file_metadata.get("url", "")
            if not url:
                # Assign a synthetic URL based on filename for comprehensive files
                url = self._get_synthetic_url(path)
                file_metadata["url"] = url

            page_title = file_metadata.get("title", path.stem)
            program_name = self._parse_program_name(file_metadata, path)
            metadata = {
                "source": path.relative_to(self.knowledge_dir).as_posix(),
                "source_filename": path.name,
                "file_path": str(path),
                "page_title": page_title,
                "url": url,
                "category": file_metadata.get("category", ""),
                "program_name": program_name,
                "last_scraped": file_metadata.get("last scraped", ""),
                "document_type": path.suffix.lower().lstrip("."),
            }
            documents.append(Document(page_content=body, metadata=metadata))

        return documents

    def _get_synthetic_url(self, path: Path) -> str:
        """Generate synthetic URL for comprehensive files."""
        stem = path.stem.lower()
        if "online_mca" in stem or "mca" in stem:
            return "https://charusat.online/programs/mca.html"
        elif "online_bca" in stem or "bca" in stem:
            return "https://charusat.online/programs/bca.html"
        elif "online_bba" in stem or "bba" in stem:
            return "https://charusat.online/programs/bba.html"
        elif "online_mba" in stem or "mba" in stem:
            return "https://charusat.online/programs/mba.html"
        elif "admissions" in stem or "refund" in stem:
            return "https://charusat.online/"
        elif "examination" in stem or "aicte" in stem or "eoa" in stem:
            return "https://charusat.online/"
        elif "contact" in stem:
            return "https://charusat.online/programs/contact.html"
        else:
            return "https://charusat.online/"

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents using semantic-aware chunking for better retrieval."""
        chunks: List[Document] = []

        for doc in documents:
            content = doc.page_content
            metadata = dict(doc.metadata)

            # Detect content type and apply appropriate chunking strategy
            if self._is_markdown_document(content):
                doc_chunks = self._semantic_markdown_split(content, metadata)
            elif self._is_table_heavy(content):
                doc_chunks = self._table_aware_split(content, metadata)
            else:
                doc_chunks = self._standard_recursive_split(content, metadata)

            chunks.extend(doc_chunks)

        chunks = deduplicate_chunks(chunks)
        print_info(f"Chunks created: {len(chunks)}")
        logger.info("Chunks created: %s", len(chunks))
        return chunks

    def _is_markdown_document(self, content: str) -> bool:
        """Check if content has markdown structure (headers, lists)."""
        return bool(re.search(r"^#{1,6}\s", content, re.MULTILINE) or
                   re.search(r"^[\*\-\+]\s", content, re.MULTILINE))

    def _is_table_heavy(self, content: str) -> bool:
        """Check if content has significant table data."""
        table_lines = [l for l in content.splitlines() if l.strip().startswith("|")]
        total_lines = len([l for l in content.splitlines() if l.strip()])
        return len(table_lines) > total_lines * 0.3

    def _semantic_markdown_split(self, content: str, metadata: dict) -> List[Document]:
        """Split markdown content preserving semantic boundaries."""
        splitter = MarkdownTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        raw_chunks = splitter.split_text(content)
        return self._finalize_chunks(raw_chunks, metadata)

    def _table_aware_split(self, content: str, metadata: dict) -> List[Document]:
        """Split content with tables, keeping tables intact when possible."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
        )
        raw_chunks = splitter.split_text(content)
        return self._finalize_chunks(raw_chunks, metadata)

    def _standard_recursive_split(self, content: str, metadata: dict) -> List[Document]:
        """Standard recursive text splitting for plain content."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
        )
        raw_chunks = splitter.split_text(content)
        return self._finalize_chunks(raw_chunks, metadata)

    def _finalize_chunks(self, raw_chunks: List[str], metadata: dict) -> List[Document]:
        """Convert raw text chunks to Document objects with validation."""
        chunks: List[Document] = []
        for index, text in enumerate(raw_chunks, start=1):
            if not is_valid_chunk(text):
                continue
            chunk_metadata = dict(metadata)
            chunk_metadata["chunk_id"] = index
            chunks.append(Document(page_content=text, metadata=chunk_metadata))
        return chunks

    def reset_vector_store(self) -> None:
        if self.vector_dir.exists():
            try:
                shutil.rmtree(self.vector_dir)
            except Exception:
                shutil.rmtree(self.vector_dir, ignore_errors=True)
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        print_info("Rebuilt vector database directory.")

    def build_source_manifest(self) -> dict[str, Any]:
        files = self.get_source_files()
        payload: List[dict[str, Any]] = []
        for path in files:
            payload.append(
                {
                    "path": path.relative_to(self.knowledge_dir).as_posix(),
                    "size": path.stat().st_size,
                    "modified": int(path.stat().st_mtime),
                }
            )
        return {"files": payload}

    def write_source_manifest(self) -> None:
        self.manifest_path.write_text(json.dumps(self.build_source_manifest(), indent=2), encoding="utf-8")

    def should_rebuild_vector_store(self) -> bool:
        if not self.vector_dir.exists():
            return True
        if not self.manifest_path.exists():
            return True

        try:
            stored = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return True

        return stored != self.build_source_manifest()


if __name__ == "__main__":
    ingester = KnowledgeBaseIngester()
    docs = ingester.load_documents()
    chunks = ingester.split_documents(docs)
    print_warning(f"Prepared {len(chunks)} chunks for embedding.")
