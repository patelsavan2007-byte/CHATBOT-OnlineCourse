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
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 5

load_dotenv(BASE_DIR / ".env")


def get_api_key() -> Optional[str]:
    """Return the configured Gemini or OpenAI API key if present."""
    for env_name in ("GOOGLE_API_KEY", "OPENAI_API_KEY"):
        value = os.getenv(env_name)
        if value:
            return value
    return None


def ensure_directories() -> None:
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
