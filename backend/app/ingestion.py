from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import CHUNK_OVERLAP, CHUNK_SIZE, KNOWLEDGE_BASE_DIR, VECTOR_DB_DIR
from app.utils import logger, print_info, print_warning


class KnowledgeBaseIngester:
    def __init__(self) -> None:
        self.knowledge_dir = KNOWLEDGE_BASE_DIR
        self.vector_dir = VECTOR_DB_DIR

    def load_documents(self) -> List[Document]:
        documents: List[Document] = []
        if not self.knowledge_dir.exists():
            raise FileNotFoundError(f"Knowledge base folder not found: {self.knowledge_dir}")

        files = sorted(self.knowledge_dir.glob("*.txt")) + sorted(self.knowledge_dir.glob("*.md"))
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
                "source": path.name,
                "filename": path.name,
                "document_type": path.suffix.lower().lstrip("."),
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


if __name__ == "__main__":
    ingester = KnowledgeBaseIngester()
    docs = ingester.load_documents()
    chunks = ingester.split_documents(docs)
    print_warning(f"Prepared {len(chunks)} chunks for embedding.")
