"""Ingest PDF files into the existing ChromaDB vector store.

Usage:
    python ingest_pdfs.py                              # Ingest all PDFs from knowledge_base/pdfs/
    python ingest_pdfs.py --file "PPR_Online MBA.pdf"  # Ingest a specific PDF
    python ingest_pdfs.py --clear-pdfs                 # Remove all PDF docs, then re-ingest
    python ingest_pdfs.py --list                       # List available PDFs
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import PDF_DIR, ensure_directories
from app.pdf_ingestion import (
    PDFIngester,
    ingest_pdfs_to_vectordb,
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_TABLE,
    CONTENT_TYPE_IMAGE,
)
from app.utils import print_info, print_section, print_warning


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest PDF files into the CHARUSAT RAG vector store."
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Specific PDF filename to ingest (must be in knowledge_base/pdfs/).",
    )
    parser.add_argument(
        "--clear-pdfs",
        action="store_true",
        help="Remove all existing PDF documents from ChromaDB before ingesting.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_pdfs",
        help="List available PDF files and exit.",
    )
    args = parser.parse_args()

    ensure_directories()
    print_section("CHARUSAT PDF Ingestion Pipeline")

    ingester = PDFIngester()

    # List mode
    if args.list_pdfs:
        files = ingester.get_pdf_files()
        if not files:
            print_warning("No PDF files found in knowledge_base/pdfs/")
        else:
            print_info(f"Found {len(files)} PDF file(s):")
            for f in files:
                size_kb = f.stat().st_size / 1024
                print_info(f"  - {f.name} ({size_kb:.1f} KB)")
        return

    # Discover PDFs
    if args.file:
        pdf_path = PDF_DIR / args.file
        if not pdf_path.exists():
            print_warning(f"PDF not found: {pdf_path}")
            return
        pdf_files = [pdf_path]
    else:
        pdf_files = ingester.get_pdf_files()

    if not pdf_files:
        print_warning("No PDF files found in knowledge_base/pdfs/")
        return

    # Print discovery summary
    print_info(f"PDF directory: {PDF_DIR}")
    print_info(f"Found PDFs:")
    for f in pdf_files:
        size_kb = f.stat().st_size / 1024
        print_info(f"  - {f.name} ({size_kb:.1f} KB)")
    print_info("")

    if args.clear_pdfs:
        print_warning("Will clear existing PDF documents before ingesting.")

    # Run ingestion with per-file detail
    chunks_added = ingest_pdfs_to_vectordb(
        specific_file=args.file,
        clear_existing_pdfs=args.clear_pdfs,
    )

    # Show ChromaDB total count
    try:
        from app.embeddings import EmbeddingStore
        store = EmbeddingStore()
        vs = store.load_vector_store()
        total_docs = vs._collection.count()
    except Exception:
        total_docs = "unknown"

    print_info("")
    print_info("=" * 60)
    print_info(f"Total PDF Chunks Added This Run : {chunks_added}")
    print_info(f"Total Documents in ChromaDB     : {total_docs}")
    print_info("PDF Ingestion Complete")
    print_info("=" * 60)


if __name__ == "__main__":
    main()
