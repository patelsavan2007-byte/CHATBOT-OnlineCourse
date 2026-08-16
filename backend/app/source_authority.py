"""General source-authority scoring for retrieved chunks.

Source authority reflects how official/authoritative a document is for the
university's online programmes (official programme PDFs > official website
programme pages > general policy pages > other indexed documents).

Authority is used as a small, bounded bonus on top of semantic relevance so
that, all else being equal, information from a more authoritative source is
preferred. It never overrides a large semantic relevance difference, and it
never causes a lower-priority source to be discarded outright.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

from app import config
from app.utils import logger


class SourceAuthority:
    """Configurable source-priority resolver for document metadata."""

    @classmethod
    def priority(cls, metadata: Dict[str, object]) -> float:
        """Return the base authority priority (0..1) for a chunk's metadata.

        Matches ``<source> <document_type>`` against the configured
        SOURCE_AUTHORITY_TIERS and returns the highest matching priority.
        """
        source = str(metadata.get("source", ""))
        doc_type = str(metadata.get("document_type", ""))
        text = f"{source} {doc_type}".lower()

        best = 0.0
        for pattern, priority in config.SOURCE_AUTHORITY_TIERS:
            if re.search(pattern, text, re.IGNORECASE):
                if priority > best:
                    best = priority
        return best

    @classmethod
    def authority_bonus(
        cls,
        metadata: Dict[str, object],
        query_program: str = "",
    ) -> float:
        """Return the bounded score bonus contributed by source authority.

        A programme-specific chunk whose programme matches the programme
        detected in the query receives a priority bump so the official
        programme source is preferred among otherwise-equivalent chunks.
        """
        priority = cls.priority(metadata)
        if query_program:
            chunk_program = metadata.get("program_name", "")
            if chunk_program == query_program:
                priority += config.PROGRAMME_MATCH_PRIORITY_BONUS

        bonus = config.SOURCE_AUTHORITY_WEIGHT * priority
        capped = min(bonus, config.SOURCE_AUTHORITY_MAX_BONUS)
        return capped

    @classmethod
    def describe(cls, metadata: Dict[str, object]) -> Optional[str]:
        """Return a short human-readable authority label (for logging only)."""
        if not config.SOURCE_AUTHORITY_ENABLED:
            return None
        priority = cls.priority(metadata)
        if priority >= 0.95:
            return "official"
        if priority >= 0.85:
            return "official-programme"
        if priority >= 0.70:
            return "official-policy"
        if priority > 0.0:
            return "general"
        return None


def source_authority_bonus(
    metadata: Dict[str, object],
    query_program: str = "",
) -> float:
    """Convenience wrapper used by the retriever."""
    if not config.SOURCE_AUTHORITY_ENABLED:
        return 0.0
    bonus = SourceAuthority.authority_bonus(metadata, query_program)
    if bonus > 0:
        label = SourceAuthority.describe(metadata)
        logger.debug(
            "Source authority bonus %.3f (%s) for %s",
            bonus, label or "unclassified",
            metadata.get("source", "unknown"),
        )
    return bonus
