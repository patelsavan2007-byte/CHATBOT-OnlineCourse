"""Citation extraction and validation for chatbot responses.

Ensures at most 3 citations with score >= MIN_SOURCE_SCORE that share
numbers or key terms with the final answer text. Omits citations for
not-found or small-talk responses.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document

from app import config
from app.utils import logger


def extract_citations(
    retrieved: List[Tuple[Document, float]],
    answer_text: str = "",
    min_score: Optional[float] = None,
    max_citations: int = 3,
) -> List[Dict[str, Any]]:
    """Extract and deduplicate up to max_citations supported sources."""
    if not answer_text or not retrieved:
        return []

    lowered_ans = answer_text.lower()
    # None for pure not-found or conversational scope fallbacks
    if "[[not_found]]" in lowered_ans or lowered_ans.startswith("i couldn't find"):
        return []

    threshold = min_score if min_score is not None else getattr(config, "MIN_SOURCE_SCORE", 0.60)

    # Extract numbers from answer (e.g. 50000, 1500, 164000, 2, 3, 4)
    raw_numbers = re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", answer_text)
    clean_numbers = [n.replace(",", "") for n in raw_numbers]

    # Distinctive content words from answer (including acronyms like bba, bca, mba, mca, ugc, lms)
    stopwords = {
        "this", "that", "with", "from", "have", "will", "your", "official",
        "please", "contact", "about", "which", "there", "their", "where",
        "tell", "give", "full", "information", "available"
    }
    answer_words = {w for w in re.findall(r"\b[a-zA-Z]{3,}\b", lowered_ans) if w not in stopwords}

    candidates = []
    seen = set()

    for doc, score in retrieved:
        if score < threshold:
            continue

        meta = doc.metadata
        source_path = str(meta.get("source", ""))
        page = meta.get("page")
        url = meta.get("url")
        cid = meta.get("chunk_id")
        key = (source_path, page or url or cid)
        if key in seen:
            continue

        doc_lower = doc.page_content.lower()

        # Check support: shared numbers (with word boundary) or distinctive terms
        shares_num = any(re.search(r"\b" + re.escape(num) + r"\b", doc_lower) for num in clean_numbers) if clean_numbers else False
        doc_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", doc_lower))
        shared_terms = len(answer_words & doc_words)

        if shares_num or shared_terms >= 1:
            seen.add(key)
            src_item: Dict[str, Any] = {
                "source": source_path,
                "page": page,
                "program": meta.get("program_name"),
                "score": round(score, 3),
            }
            if url:
                src_item["url"] = url
            candidates.append((src_item, score, 1 if shares_num else 0, shared_terms))

    # Sort candidates by number match, score, and term overlap
    candidates.sort(key=lambda x: (x[2], x[1], x[3]), reverse=True)
    return [c[0] for c in candidates[:max_citations]]
