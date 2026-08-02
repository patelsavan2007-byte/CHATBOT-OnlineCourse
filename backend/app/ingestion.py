from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import CHUNK_OVERLAP, CHUNK_SIZE, KNOWLEDGE_BASE_DIR, VECTOR_DB_DIR
from app.scraper import crawl_internal_pages
from app.utils import logger, print_info, print_warning


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

        if stem == "online_bca" or url_path.endswith("/programs/bca.html") or url_path.endswith("/programs/bca"):
            return "online_bca"
        if stem == "online_bba" or url_path.endswith("/programs/bba.html") or url_path.endswith("/programs/bba"):
            return "online_bba"
        if stem == "online_mba" or url_path.endswith("/programs/mba.html") or url_path.endswith("/programs/mba"):
            return "online_mba"
        if stem == "online_mca" or url_path.endswith("/programs/mca.html") or url_path.endswith("/programs/mca"):
            return "online_mca"
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
            if not file_metadata.get("url"):
                logger.warning("Skipping non-scraped markdown file %s", path)
                continue

            page_title = file_metadata.get("title", path.stem)
            program_name = self._parse_program_name(file_metadata, path)
            metadata = {
                "source": path.relative_to(self.knowledge_dir).as_posix(),
                "source_filename": path.name,
                "file_path": str(path),
                "page_title": page_title,
                "url": file_metadata.get("url", ""),
                "category": file_metadata.get("category", ""),
                "program_name": program_name,
                "last_scraped": file_metadata.get("last scraped", ""),
                "document_type": path.suffix.lower().lstrip("."),
            }
            documents.append(Document(page_content=body, metadata=metadata))

        return documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
        )
        chunks: List[Document] = []
        for doc in documents:
            doc_chunks = splitter.split_documents([doc])
            for index, chunk in enumerate(doc_chunks, start=1):
                metadata = dict(doc.metadata)
                metadata["chunk_id"] = index
                chunk.metadata = metadata
                chunks.append(chunk)

        print_info(f"Chunks created: {len(chunks)}")
        logger.info("Chunks created: %s", len(chunks))
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
