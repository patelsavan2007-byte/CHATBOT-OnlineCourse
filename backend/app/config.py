from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
VECTOR_DB_DIR = BASE_DIR / "vector_db"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
FALLBACK_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
TOP_K = 5
SCRAPE_START_URL = "https://charusat.online/"
SCRAPE_MAX_PAGES = 250
CRAWL_DELAY = 0.5

load_dotenv(BASE_DIR / ".env")


def get_api_key() -> Optional[str]:
    """Return the configured GOOGLE_API_KEY from .env if present."""
    key = os.getenv("GOOGLE_API_KEY")
    if key and key.strip() and not key.startswith("#"):
        return key.strip()
    return None


def ensure_directories() -> None:
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
