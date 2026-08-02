from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import CHUNK_OVERLAP, CHUNK_SIZE, KNOWLEDGE_BASE_DIR, VECTOR_DB_DIR
from app.scraper import crawl_internal_pages
from app.utils import logger, print_info, print_warning


class KnowledgeBaseIngester:
    def __init__(self) -> None:
        self.knowledge_dir = KNOWLEDGE_BASE_DIR
        self.vector_dir = VECTOR_DB_DIR
        self.manifest_path = self.vector_dir / "source_manifest.json"

    def refresh_sources(self) -> List[Path]:
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.vector_dir.mkdir(parents=True, exist_ok=True)

        try:
            scraped_files = crawl_internal_pages(output_dir=self.knowledge_dir / "scraped")
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
            if path.is_file() and path.suffix.lower() in {".txt", ".md"}
            and "__pycache__" not in path.parts
            and "vector_db" not in path.parts
        ]
        return sorted(files)

    def load_documents(self) -> List[Document]:
        documents: List[Document] = []
        files = self.get_source_files()
        if not files:
            self.refresh_sources()
            files = self.get_source_files()

        if not files:
            raise ValueError("No .txt or .md files found in the knowledge base directory.")

        print_info(f"Loaded files: {', '.join(path.name for path in files)}")
        logger.info("Loaded files: %s", ", ".join(path.name for path in files))

        for path in files:
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"Corrupted file: {path.name}") from exc

            metadata = {
                "source": path.relative_to(self.knowledge_dir).as_posix(),
                "filename": path.name,
                "document_type": path.suffix.lower().lstrip("."),
                "path": str(path),
            }
            documents.append(Document(page_content=content, metadata=metadata))

        return documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
        )
        chunks = splitter.split_documents(documents)
        for index, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = index + 1
        print_info(f"Chunks created: {len(chunks)}")
        logger.info("Chunks created: %s", len(chunks))
        return chunks

    def reset_vector_store(self) -> None:
        if self.vector_dir.exists():
            shutil.rmtree(self.vector_dir)
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
