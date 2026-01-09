"""Caching utilities for API responses.

Provides in-memory caching with TTL to reduce API calls.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    """A single cache entry with TTL tracking."""
    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)


class Cache:
    """In-memory cache with TTL support.

    Provides caching for API responses to reduce repeated calls.
    """

    _instance: "Cache | None" = None

    def __new__(cls) -> "Cache":
        """Singleton pattern for global cache."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        """Initialize cache state."""
        self._cache: dict[str, CacheEntry] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._default_ttl: int = 300  # 5 minutes

    @property
    def default_ttl(self) -> int:
        """Get default TTL in seconds."""
        return self._default_ttl

    @default_ttl.setter
    def default_ttl(self, value: int) -> None:
        """Set default TTL in seconds."""
        self._default_ttl = value

    def get(self, key: str) -> Any | None:
        """Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None

        if time.time() > entry.expires_at:
            # Entry expired
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl or self._default_ttl
        self._cache[key] = CacheEntry(
            value=value,
            expires_at=time.time() + ttl,
        )

    def delete(self, key: str) -> bool:
        """Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            True if key existed
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    def clear_expired(self) -> int:
        """Clear only expired entries.

        Returns:
            Number of entries cleared
        """
        now = time.time()
        expired = [k for k, v in self._cache.items() if now > v.expires_at]
        for key in expired:
            del self._cache[key]
        return len(expired)

    def clear_prefix(self, prefix: str) -> int:
        """Clear all entries with a key prefix.

        Args:
            prefix: Key prefix to match

        Returns:
            Number of entries cleared
        """
        matching = [k for k in self._cache.keys() if k.startswith(prefix)]
        for key in matching:
            del self._cache[key]
        return len(matching)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        now = time.time()
        total = len(self._cache)
        expired = sum(1 for v in self._cache.values() if now > v.expires_at)
        active = total - expired

        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "total_entries": total,
            "active_entries": active,
            "expired_entries": expired,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "default_ttl": self._default_ttl,
        }

    def reset_stats(self) -> None:
        """Reset hit/miss statistics."""
        self._hits = 0
        self._misses = 0

    def keys(self) -> list[str]:
        """Get all cache keys.

        Returns:
            List of cache keys
        """
        return list(self._cache.keys())


# Global cache instance
cache = Cache()


def cached(ttl: int | None = None, prefix: str = ""):
    """Decorator for caching function results.

    Args:
        ttl: Cache TTL in seconds
        prefix: Key prefix for cache entries

    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            key_parts = [prefix, func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = ":".join(key_parts)

            # Check cache
            result = cache.get(key)
            if result is not None:
                return result

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl=ttl)
            return result

        return wrapper
    return decorator
