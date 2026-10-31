#!/usr/bin/env python3
"""validate_starters.py - Runs question bank questions through RAG retrieval
against the vector store to verify they retrieve good chunks and answer
without falling back, producing frontend/src/data/validated_starters.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# Ensure offline vector DB fallback
if "VECTOR_DB_DIR" not in os.environ:
    copy_dir = Path("C:/AProjects/CHATB-vector-db-copy-20261031")
    if copy_dir.exists():
        os.environ["VECTOR_DB_DIR"] = str(copy_dir)

from app.conversation import analyze_turn
from app.embeddings import EmbeddingStore
from app.retriever import RAGRetriever


def validate_question_bank(
    qb_path: Path,
    output_path: Path,
    min_score: float = 0.52,
) -> list[str]:
    """Validate all question bank items against retriever and write validated IDs."""
    if not qb_path.exists():
        raise FileNotFoundError(f"Question bank not found at {qb_path}")

    with open(qb_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    vector_db_path = os.getenv("VECTOR_DB_DIR", str(BACKEND_DIR / "vector_db"))
    store = EmbeddingStore(persist_directory=vector_db_path)
    vector_store = store.load_vector_store()
    retriever = RAGRetriever(vector_store)

    validated_ids = []
    validated_records = []
    rejected = []

    for item in questions:
        qid = item.get("id", "")
        text = item.get("text", "")
        status = item.get("status", "")
        topics = item.get("topics", ["general"])
        topic = topics[0] if topics else "general"

        if status == "NOT_IN_DOCS":
            rejected.append((qid, text, "marked NOT_IN_DOCS in question bank"))
            continue

        plan = analyze_turn(text)
        results = retriever.retrieve(text, plan=plan)

        if not results:
            rejected.append((qid, text, "no chunks retrieved"))
            continue

        top_doc, top_score = results[0]
        if top_score < min_score:
            rejected.append((qid, text, f"score {top_score:.3f} below threshold {min_score}"))
            continue

        validated_ids.append(qid)
        validated_records.append(
            {
                "id": qid,
                "text": text,
                "topic": topic,
                "category": item.get("category", "General"),
                "score": round(top_score, 3),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(validated_ids, f, indent=2)

    print(f"Validation complete: {len(validated_ids)} validated, {len(rejected)} rejected.")
    print(f"Validated IDs written to {output_path}")
    return validated_ids


if __name__ == "__main__":
    qb_file = BACKEND_DIR / "app" / "data" / "question_bank.json"
    out_file = ROOT_DIR / "frontend" / "src" / "data" / "validated_starters.json"
    validate_question_bank(qb_file, out_file)
