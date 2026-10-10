"""Caching layer for repeated questions and performance optimization.

This module provides:
- In-memory caching of question-answer pairs
- TTL-based cache expiration
- Cache statistics for monitoring
- Integration with latency metrics
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional, Tuple

from app import config
from app.utils import logger


class CacheEntry:
    """Single cache entry with metadata."""

    def __init__(
        self,
        answer: str,
        sources: list,
        timestamp: float,
        ttl: int,
    ) -> None:
        """Initialize cache entry.

        Args:
            answer: Cached answer
            sources: Cached sources
            timestamp: Creation timestamp
            ttl: Time-to-live in seconds
        """
        self.answer = answer
        self.sources = sources
        self.timestamp = timestamp
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() - self.timestamp > self.ttl


class QuestionCache:
    """In-memory cache for question-answer pairs."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600) -> None:
        """Initialize question cache.

        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def _generate_key(self, question: str) -> str:
        """Generate cache key from question.

        Args:
            question: User question

        Returns:
            Cache key (hash)
        """
        # Normalize question for caching
        normalized = question.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, question: str) -> Optional[Tuple[str, list]]:
        """Get cached answer for question.

        Args:
            question: User question

        Returns:
            Tuple of (answer, sources) if found and not expired, None otherwise
        """
        key = self._generate_key(question)
        entry = self.cache.get(key)

        if entry is None:
            self.misses += 1
            return None

        if entry.is_expired():
            # Remove expired entry
            del self.cache[key]
            self.misses += 1
            logger.info("Cache entry expired for question: %s", question[:50])
            return None

        self.hits += 1
        logger.info("Cache hit for question: %s", question[:50])
        return entry.answer, entry.sources

    def set(
        self,
        question: str,
        answer: str,
        sources: list,
        ttl: Optional[int] = None,
    ) -> None:
        """Cache answer for question.

        Args:
            question: User question
            answer: Generated answer
            sources: Retrieved sources
            ttl: Custom time-to-live in seconds
        """
        # Check cache size limit
        if len(self.cache) >= self.max_size:
            # Remove oldest entry (simple eviction strategy)
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
            del self.cache[oldest_key]
            logger.info("Cache eviction: removed oldest entry")

        key = self._generate_key(question)
        entry_ttl = ttl or self.default_ttl
        self.cache[key] = CacheEntry(answer, sources, time.time(), entry_ttl)
        logger.info("Cached answer for question: %s (TTL: %ds)", question[:50], entry_ttl)

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 3),
        }

    def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.info("Cleaned up %d expired cache entries", len(expired_keys))

        return len(expired_keys)


# Global cache instance
_global_cache: Optional[QuestionCache] = None


def get_cache() -> QuestionCache:
    """Get global cache instance.

    Returns:
        QuestionCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = QuestionCache()
        logger.info("Global cache initialized")
    return _global_cache
