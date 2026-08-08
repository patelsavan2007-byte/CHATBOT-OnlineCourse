"""PDF ingestion module for the CHARUSAT RAG pipeline.

Extracts text and tables from PDF files, preserving page numbers and
structural metadata. Designed to be modular so a vision/multimodal
retrieval layer can be added later without rewriting.

Content types supported (extensible):
  - "text"   : regular paragraph/section text
  - "table"  : tabular data extracted via pymupdf
  - "image"  : (future) page renders or embedded images
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymupdf as fitz  # pymupdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import (
    CHUNK_OVERLAP,
    KNOWLEDGE_BASE_DIR,
    PDF_CHUNK_SIZE,
    PDF_DIR,
    PDF_TABLE_CHUNK_SIZE,
)
from app.utils import logger, print_info, print_warning


# ---------------------------------------------------------------------------
# Supported content types (multimodal-ready enum-like constants)
# ---------------------------------------------------------------------------
CONTENT_TYPE_TEXT = "text"
CONTENT_TYPE_TABLE = "table"
CONTENT_TYPE_IMAGE = "image"  # placeholder for future multimodal support


# ---------------------------------------------------------------------------
# Programme detection from PDF filename / content
# ---------------------------------------------------------------------------
_PROGRAMME_PATTERNS: Dict[str, str] = {
    r"\bmba\b": "online_mba",
    r"\bbca\b": "online_bca",
    r"\bbba\b": "online_bba",
    r"\bmca\b": "online_mca",
}


def _detect_programme(text: str) -> str:
    """Detect programme name from text (filename, title, content).

    Returns a programme name like 'online_mba', or 'general' for
    non-programme documents (e.g. Fees Refund Policy).
    """
    text_lower = text.lower()
    for pattern, programme in _PROGRAMME_PATTERNS.items():
        if re.search(pattern, text_lower):
            return programme
    return "general"


# ---------------------------------------------------------------------------
# Text cleaning helpers
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Clean extracted PDF text: fix encoding artefacts, normalise whitespace."""
    # Replace common PDF encoding artefacts
    replacements = {
        "\uf0b7": "•",     # bullet
        "\u2019": "'",     # right single quote
        "\u2013": "–",     # en-dash
        "\u2014": "—",     # em-dash
        "\u2018": "'",     # left single quote
        "\u201c": '"',     # left double quote
        "\u201d": '"',     # right double quote
        "ΓÇÖ": "'",
        "ΓÇô": "–",
        "∩Çá": "",
        "Γëæ": "Σ",
        "ΓëÑ": "≥",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip page header/footer artefacts like "1 | P a g e"
    text = re.sub(r"\d+\s*\|\s*P\s*a\s*g\s*e\s*", "", text)
    return text.strip()


def _table_to_markdown(table_data: List[List[str]]) -> str:
    """Convert a 2D list of cell values into a Markdown table string."""
    if not table_data or not table_data[0]:
        return ""

    def _cell(val: Any) -> str:
        s = str(val) if val is not None else ""
        # Replace newlines inside cells with spaces
        return s.replace("\n", " ").strip()

    rows = [[_cell(c) for c in row] for row in table_data]

    # Use first row as header
    header = rows[0]
    col_widths = [max(len(header[i]), *(len(r[i]) for r in rows[1:])) for i in range(len(header))] if len(rows) > 1 else [len(h) for h in header]

    lines: List[str] = []
    # Header row
    lines.append("| " + " | ".join(h.ljust(w) for h, w in zip(header, col_widths)) + " |")
    # Separator
    lines.append("| " + " | ".join("-" * w for w in col_widths) + " |")
    # Data rows
    for row in rows[1:]:
        lines.append("| " + " | ".join(c.ljust(w) for c, w in zip(row, col_widths)) + " |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core PDF extraction
# ---------------------------------------------------------------------------

class PDFIngester:
    """Extract text and tables from PDFs in the knowledge_base/pdfs/ directory.

    Produces LangChain Document objects with rich metadata suitable for
    the existing ChromaDB vector store.
    """

    def __init__(self, pdf_dir: Optional[Path] = None) -> None:
        self.pdf_dir = pdf_dir or PDF_DIR

    # ---- public API -------------------------------------------------------

    def get_pdf_files(self) -> List[Path]:
        """Return sorted list of PDF files in the pdf directory."""
        if not self.pdf_dir.exists():
            self.pdf_dir.mkdir(parents=True, exist_ok=True)
            return []
        return sorted(
            p for p in self.pdf_dir.iterdir()
            if p.is_file() and p.suffix.lower() == ".pdf"
        )

    def load_pdf_documents(
        self,
        specific_file: Optional[str] = None,
    ) -> List[Document]:
        """Load and extract documents from PDFs.

        Args:
            specific_file: If given, only process this filename from the pdf dir.

        Returns:
            List of Document objects (one per extracted segment: text or table).
        """
        if specific_file:
            path = self.pdf_dir / specific_file
            if not path.exists():
                raise FileNotFoundError(f"PDF not found: {path}")
            pdf_files = [path]
        else:
            pdf_files = self.get_pdf_files()

        if not pdf_files:
            print_warning("No PDF files found in knowledge_base/pdfs/")
            return []

        all_documents: List[Document] = []
        for pdf_path in pdf_files:
            print_info(f"Processing PDF: {pdf_path.name}")
            logger.info("Processing PDF: %s", pdf_path.name)
            docs = self._extract_from_pdf(pdf_path)
            all_documents.extend(docs)
            print_info(f"  Extracted {len(docs)} segments from {pdf_path.name}")

        return all_documents

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Chunk extracted PDF documents using the project's chunking strategy.

        Text segments use PDF_CHUNK_SIZE (800).
        Table segments use PDF_TABLE_CHUNK_SIZE (1200) to preserve table rows.
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=PDF_CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
        )
        table_splitter = RecursiveCharacterTextSplitter(
            chunk_size=PDF_TABLE_CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", "| ", " ", ""],
        )

        chunks: List[Document] = []
        # Group documents by source file for consistent chunk_id numbering
        docs_by_source: Dict[str, List[Document]] = {}
        for doc in documents:
            key = doc.metadata.get("filename", "unknown")
            docs_by_source.setdefault(key, []).append(doc)

        for filename, file_docs in docs_by_source.items():
            chunk_counter = 0
            for doc in file_docs:
                content_type = doc.metadata.get("content_type", CONTENT_TYPE_TEXT)
                splitter = table_splitter if content_type == CONTENT_TYPE_TABLE else text_splitter

                doc_chunks = splitter.split_documents([doc])
                for chunk in doc_chunks:
                    chunk_counter += 1
                    metadata = dict(doc.metadata)
                    metadata["chunk_id"] = chunk_counter
                    chunk.metadata = metadata
                    chunks.append(chunk)

        print_info(f"PDF chunks created: {len(chunks)}")
        logger.info("PDF chunks created: %s", len(chunks))
        return chunks

    # ---- internal extraction ----------------------------------------------

    def _extract_from_pdf(self, pdf_path: Path) -> List[Document]:
        """Extract text and table segments from a single PDF."""
        documents: List[Document] = []
        programme = _detect_programme(pdf_path.stem)

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as exc:
            print_warning(f"Failed to open PDF {pdf_path.name}: {exc}")
            logger.error("Failed to open PDF %s: %s", pdf_path.name, exc)
            return []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_num = page_idx + 1  # 1-indexed

            base_metadata = {
                "source": f"pdfs/{pdf_path.name}",
                "filename": pdf_path.name,
                "page": page_num,
                "document_type": "pdf",
                "program_name": programme,
            }

            # ---- Extract tables first ------------------------------------
            table_regions: List[fitz.Rect] = []
            try:
                table_finder = page.find_tables()
                for table_idx, table in enumerate(table_finder.tables):
                    table_regions.append(fitz.Rect(table.bbox))
                    table_doc = self._table_to_document(
                        table, page_num, table_idx, base_metadata
                    )
                    if table_doc:
                        documents.append(table_doc)
            except Exception as exc:
                logger.warning(
                    "Table extraction failed on page %d of %s: %s",
                    page_num, pdf_path.name, exc,
                )

            # ---- Extract text (excluding table regions) -------------------
            text = self._extract_text_excluding_tables(page, table_regions)
            text = _clean_text(text)

            if text and len(text.strip()) > 30:
                text_metadata = dict(base_metadata)
                text_metadata["content_type"] = CONTENT_TYPE_TEXT
                documents.append(
                    Document(page_content=text, metadata=text_metadata)
                )

        doc.close()
        return documents

    def _table_to_document(
        self,
        table: Any,
        page_num: int,
        table_idx: int,
        base_metadata: Dict[str, Any],
    ) -> Optional[Document]:
        """Convert a pymupdf table object to a Document with markdown content."""
        try:
            # Extract raw cell data
            data = table.extract()
            if not data or len(data) < 2:
                return None

            markdown = _table_to_markdown(data)
            if not markdown or len(markdown.strip()) < 20:
                return None

            metadata = dict(base_metadata)
            metadata["content_type"] = CONTENT_TYPE_TABLE
            metadata["table_index"] = table_idx

            return Document(page_content=markdown, metadata=metadata)
        except Exception as exc:
            logger.warning(
                "Failed to convert table %d on page %d: %s",
                table_idx, page_num, exc,
            )
            return None

    def _extract_text_excluding_tables(
        self,
        page: Any,
        table_rects: List[Any],
    ) -> str:
        """Extract page text while excluding regions covered by detected tables."""
        if not table_rects:
            return page.get_text("text")

        # Get text blocks and filter out those that overlap with table regions
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        text_parts: List[str] = []

        for block in blocks:
            if block["type"] != 0:  # 0 = text block
                continue
            block_rect = fitz.Rect(block["bbox"])

            # Skip if this block substantially overlaps with any table
            overlaps = False
            for table_rect in table_rects:
                intersection = block_rect & table_rect
                if intersection.is_empty:
                    continue
                overlap_area = intersection.width * intersection.height
                block_area = block_rect.width * block_rect.height
                if block_area > 0 and (overlap_area / block_area) > 0.5:
                    overlaps = True
                    break

            if not overlaps:
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    if line_text.strip():
                        text_parts.append(line_text)

        return "\n".join(text_parts)


# ---------------------------------------------------------------------------
# Convenience function for standalone usage
# ---------------------------------------------------------------------------

def ingest_pdfs_to_vectordb(
    specific_file: Optional[str] = None,
    clear_existing_pdfs: bool = False,
) -> int:
    """Ingest PDFs into the existing ChromaDB vector store.

    This ADDS documents without rebuilding the entire database.

    Args:
        specific_file: Process only this filename.
        clear_existing_pdfs: Remove existing PDF documents before adding.

    Returns:
        Number of chunks added to the vector store.
    """
    from app.embeddings import EmbeddingStore

    ingester = PDFIngester()
    store = EmbeddingStore()
    vector_store = store.load_vector_store()

    # Optionally clear existing PDF documents
    if clear_existing_pdfs:
        _remove_pdf_documents(vector_store)

    # Extract and chunk
    documents = ingester.load_pdf_documents(specific_file=specific_file)
    if not documents:
        print_warning("No documents extracted from PDFs.")
        return 0

    chunks = ingester.chunk_documents(documents)
    if not chunks:
        print_warning("No chunks produced from PDF documents.")
        return 0

    # Print per-file extraction summary
    _print_per_file_summary(documents, chunks)

    # Remove existing documents for the same PDF file(s) to avoid duplicates
    filenames = set(c.metadata.get("filename", "") for c in chunks)
    for fname in filenames:
        _remove_documents_by_filename(vector_store, fname)

    # Add to existing vector store
    store.add_documents(chunks, vector_store=vector_store)
    print_info(f"Added {len(chunks)} PDF chunks to the vector store.")

    return len(chunks)


def _print_per_file_summary(documents: List[Document], chunks: List[Document]) -> None:
    """Print extraction summary per PDF file."""
    import pymupdf as fitz

    # Gather stats from extracted documents (pre-chunking)
    file_stats: Dict[str, Dict[str, Any]] = {}
    for doc in documents:
        fname = doc.metadata.get("filename", "unknown")
        if fname not in file_stats:
            file_stats[fname] = {
                "pages": set(),
                "text_segments": 0,
                "table_segments": 0,
                "image_segments": 0,
                "programme": doc.metadata.get("program_name", "unknown"),
            }
        file_stats[fname]["pages"].add(doc.metadata.get("page", 0))
        ct = doc.metadata.get("content_type", CONTENT_TYPE_TEXT)
        if ct == CONTENT_TYPE_TABLE:
            file_stats[fname]["table_segments"] += 1
        elif ct == CONTENT_TYPE_IMAGE:
            file_stats[fname]["image_segments"] += 1
        else:
            file_stats[fname]["text_segments"] += 1

    # Count chunks per file
    chunks_per_file: Dict[str, int] = {}
    for chunk in chunks:
        fname = chunk.metadata.get("filename", "unknown")
        chunks_per_file[fname] = chunks_per_file.get(fname, 0) + 1

    print_info("")
    print_info("-" * 60)
    print_info("Per-File Extraction Summary:")
    print_info("-" * 60)
    for fname, stats in sorted(file_stats.items()):
        num_pages = len(stats["pages"])
        print_info(f"  {fname}")
        print_info(f"    Programme    : {stats['programme']}")
        print_info(f"    Pages        : {num_pages}")
        print_info(f"    Text segments: {stats['text_segments']}")
        print_info(f"    Table segments: {stats['table_segments']}")
        if stats["image_segments"] > 0:
            print_info(f"    Image segments: {stats['image_segments']}")
        print_info(f"    Total chunks : {chunks_per_file.get(fname, 0)}")
        print_info("")


def _remove_pdf_documents(vector_store: Any) -> None:
    """Remove all documents with document_type='pdf' from the vector store."""
    try:
        collection = vector_store._collection
        results = collection.get(where={"document_type": "pdf"})
        if results and results["ids"]:
            collection.delete(ids=results["ids"])
            print_info(f"Removed {len(results['ids'])} existing PDF documents.")
            logger.info("Removed %d existing PDF documents", len(results["ids"]))
    except Exception as exc:
        logger.warning("Failed to remove existing PDF documents: %s", exc)


def _remove_documents_by_filename(vector_store: Any, filename: str) -> None:
    """Remove all documents for a specific filename to avoid duplicates on re-ingestion."""
    if not filename:
        return
    try:
        collection = vector_store._collection
        results = collection.get(where={"filename": filename})
        if results and results["ids"]:
            collection.delete(ids=results["ids"])
            print_info(f"Removed {len(results['ids'])} existing chunks for '{filename}'.")
            logger.info(
                "Removed %d existing chunks for '%s'",
                len(results["ids"]), filename,
            )
    except Exception as exc:
        logger.warning("Failed to remove documents for '%s': %s", filename, exc)
