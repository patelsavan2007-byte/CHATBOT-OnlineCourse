"""Near-duplicate detection and diversity control for retrieved chunks.

The vector store frequently contains several chunks that convey essentially
the same information (identical table extractions, overlapping chunk
windows, the same fact repeated across pages). Without de-duplication these
near-duplicates can crowd out genuinely complementary chunks from the top-K
selection.

This module implements a deterministic, general-purpose de-duplication pass:

* two chunks are near-duplicates if their normalised text is equal, one is a
  non-trivial substring of the other, or their token-set Jaccard similarity
  exceeds a configurable threshold;
* the higher-scoring representative is kept, near-duplicates are dropped;
* a per-(source, page) cap keeps a single page from dominating the result,
  so different sections with genuinely different information are retained.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import DefaultDict, List, Optional, Tuple

from langchain_core.documents import Document

from app import config
from app.utils import logger


def normalize_text(text: str) -> str:
    """Lowercase, drop non-alphanumeric tokens and collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def token_jaccard(first: str, second: str) -> float:
    """Jaccard similarity over the token sets of two strings (0..1)."""
    tokens_a = set(normalize_text(first).split())
    tokens_b = set(normalize_text(second).split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def is_near_duplicate(
    first: str,
    second: str,
    threshold: Optional[float] = None,
) -> bool:
    """Return True if two chunk contents carry essentially the same info."""
    threshold = threshold if threshold is not None else config.DEDUP_SIMILARITY_THRESHOLD

    norm_a = normalize_text(first)
    norm_b = normalize_text(second)
    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b:
        return True

    # A substantial block embedded verbatim inside another chunk is a duplicate.
    short, long = (norm_a, norm_b) if len(norm_a) <= len(norm_b) else (norm_b, norm_a)
    if len(short) >= 40 and short in long:
        return True

    return token_jaccard(first, second) >= threshold


def deduplicate_results(
    results: List[Tuple[Document, float]],
) -> Tuple[List[Tuple[Document, float]], List[Tuple[Document, float]]]:
    """Remove near-duplicate chunks, keeping the higher-scoring representative.

    Results are expected to be sorted by score descending.

    Returns ``(kept, removed)`` where ``removed`` contains the dropped chunks
    (useful for diagnostics/logging).
    """
    if not config.DEDUP_ENABLED:
        return results, []

    # Work on a score-descending copy so the higher-scoring representative is
    # always kept regardless of the caller's ordering.
    ordered = sorted(results, key=lambda item: item[1], reverse=True)

    kept: List[Tuple[Document, float]] = []
    removed: List[Tuple[Document, float]] = []
    for doc, score in ordered:
        is_duplicate = False
        pname = doc.metadata.get("program_name", "")
        for kept_doc, _ in kept:
            kept_pname = kept_doc.metadata.get("program_name", "")
            # Chunks belonging to different programmes are never near-duplicates
            if pname and kept_pname and pname != kept_pname:
                continue
            if is_near_duplicate(doc.page_content, kept_doc.page_content):
                is_duplicate = True
                break
        if is_duplicate:
            removed.append((doc, score))
        else:
            kept.append((doc, score))

    if removed:
        logger.info("Removed %d near-duplicate chunk(s)", len(removed))
    return kept, removed


def apply_diversity_cap(
    results: List[Tuple[Document, float]],
    max_per_source_page: Optional[int] = None,
) -> Tuple[List[Tuple[Document, float]], List[Tuple[Document, float]]]:
    """Cap the number of chunks kept from the same (source, page).

    Ensures a single page cannot fill the entire top-K while different
    sections with genuinely different information remain available.

    Returns ``(kept, dropped)``.
    """
    cap = max_per_source_page if max_per_source_page is not None else config.DEDUP_MAX_PER_SOURCE_PAGE
    counts: DefaultDict[Tuple[str, object], int] = defaultdict(int)
    kept: List[Tuple[Document, float]] = []
    dropped: List[Tuple[Document, float]] = []

    for doc, score in results:
        key = (str(doc.metadata.get("source", "")), doc.metadata.get("page"))
        if counts[key] >= cap:
            dropped.append((doc, score))
            continue
        counts[key] += 1
        kept.append((doc, score))

    if dropped:
        logger.info(
            "Diversity cap removed %d chunk(s) from over-represented pages",
            len(dropped),
        )
    return kept, dropped
