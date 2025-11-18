"""
Caching layer for OSINT-85 performance optimization.

Provides multi-level caching for LLM calls, API responses, and query results.
Supports in-memory and disk-based caching with TTL and LRU eviction.
"""

import hashlib
import json
import pickle
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "total_size": self.total_size,
            "hit_rate": f"{self.hit_rate:.1f}%"
        }


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    ttl: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL."""
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl

    def touch(self):
        """Update last accessed time and increment counter."""
        self.last_accessed = time.time()
        self.access_count += 1


class Cache(ABC):
    """Abstract base class for cache implementations."""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = 3600):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of entries to store
            default_ttl: Default time-to-live in seconds (None = no expiration)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.stats = CacheStats()

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Store value in cache."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        pass

    @abstractmethod
    def clear(self):
        """Clear all cache entries."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Get current cache size."""
        pass

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.stats


class InMemoryCache(Cache):
    """In-memory LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = 3600):
        super().__init__(max_size, default_ttl)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        if key not in self._cache:
            self.stats.misses += 1
            return None

        entry = self._cache[key]

        # Check expiration
        if entry.is_expired():
            self.delete(key)
            self.stats.misses += 1
            return None

        # Update LRU order
        entry.touch()
        self._cache.move_to_end(key)

        self.stats.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Store value in cache."""
        # Use default TTL if not specified
        if ttl is None:
            ttl = self.default_ttl

        # Check if we need to evict
        if key not in self._cache and len(self._cache) >= self.max_size:
            self._evict_lru()

        # Create or update entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl
        )

        self._cache[key] = entry
        self._cache.move_to_end(key)
        self.stats.total_size = len(self._cache)

    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if key in self._cache:
            del self._cache[key]
            self.stats.total_size = len(self._cache)
            return True
        return False

    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self.stats.total_size = 0

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    def _evict_lru(self):
        """Evict least recently used entry."""
        if self._cache:
            self._cache.popitem(last=False)
            self.stats.evictions += 1
            self.stats.total_size = len(self._cache)


class DiskCache(Cache):
    """Persistent disk-based cache using pickle."""

    def __init__(self, cache_dir: Path, max_size: int = 1000, default_ttl: Optional[float] = 86400):
        super().__init__(max_size, default_ttl)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.cache_dir / "cache_index.json"
        self._index: Dict[str, Dict[str, Any]] = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load cache index from disk."""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_index(self):
        """Save cache index to disk."""
        with open(self._index_file, 'w') as f:
            json.dump(self._index, f, indent=2)

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        if key not in self._index:
            self.stats.misses += 1
            return None

        entry_meta = self._index[key]

        # Check expiration
        if entry_meta.get('ttl') is not None:
            age = time.time() - entry_meta['created_at']
            if age > entry_meta['ttl']:
                self.delete(key)
                self.stats.misses += 1
                return None

        # Load from disk
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            self.delete(key)
            self.stats.misses += 1
            return None

        try:
            with open(cache_path, 'rb') as f:
                value = pickle.load(f)

            # Update access metadata
            entry_meta['last_accessed'] = time.time()
            entry_meta['access_count'] = entry_meta.get('access_count', 0) + 1
            self._save_index()

            self.stats.hits += 1
            return value
        except Exception:
            self.delete(key)
            self.stats.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Store value in cache."""
        if ttl is None:
            ttl = self.default_ttl

        # Check if we need to evict
        if key not in self._index and len(self._index) >= self.max_size:
            self._evict_lru()

        # Save to disk
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)

            # Update index
            self._index[key] = {
                'created_at': time.time(),
                'last_accessed': time.time(),
                'ttl': ttl,
                'access_count': 0,
                'file': cache_path.name
            }
            self._save_index()
            self.stats.total_size = len(self._index)
        except Exception as e:
            # Clean up on failure
            if cache_path.exists():
                cache_path.unlink()
            raise e

    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if key in self._index:
            # Remove file
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()

            # Remove from index
            del self._index[key]
            self._save_index()
            self.stats.total_size = len(self._index)
            return True
        return False

    def clear(self):
        """Clear all cache entries."""
        # Remove all cache files
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()

        self._index.clear()
        self._save_index()
        self.stats.total_size = 0

    def size(self) -> int:
        """Get current cache size."""
        return len(self._index)

    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self._index:
            return

        # Find LRU entry
        lru_key = min(
            self._index.keys(),
            key=lambda k: self._index[k].get('last_accessed', 0)
        )

        self.delete(lru_key)
        self.stats.evictions += 1


class LLMCache:
    """Specialized cache for LLM API calls."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize LLM cache.

        Args:
            cache_dir: Directory for persistent cache (None = memory only)
        """
        if cache_dir:
            self.cache = DiskCache(
                cache_dir / "llm_cache",
                max_size=500,
                default_ttl=86400 * 7  # 7 days
            )
        else:
            self.cache = InMemoryCache(
                max_size=200,
                default_ttl=3600  # 1 hour
            )

    def _make_key(self, model: str, prompt: str, **kwargs) -> str:
        """Create cache key from LLM parameters."""
        # Include relevant parameters in key
        key_parts = [model, prompt]

        # Add relevant kwargs
        for param in ['temperature', 'max_tokens', 'system']:
            if param in kwargs:
                key_parts.append(f"{param}={kwargs[param]}")

        # Hash the combined key
        key_str = "|".join(str(p) for p in key_parts)
        return f"llm:{hashlib.sha256(key_str.encode()).hexdigest()}"

    def get(self, model: str, prompt: str, **kwargs) -> Optional[str]:
        """Get cached LLM response."""
        key = self._make_key(model, prompt, **kwargs)
        return self.cache.get(key)

    def set(self, model: str, prompt: str, response: str, **kwargs):
        """Cache LLM response."""
        key = self._make_key(model, prompt, **kwargs)
        self.cache.set(key, response)

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.cache.get_stats()

    def clear(self):
        """Clear all cached LLM responses."""
        self.cache.clear()


class APICache:
    """Specialized cache for search API responses."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize API cache.

        Args:
            cache_dir: Directory for persistent cache (None = memory only)
        """
        if cache_dir:
            self.cache = DiskCache(
                cache_dir / "api_cache",
                max_size=1000,
                default_ttl=86400  # 24 hours
            )
        else:
            self.cache = InMemoryCache(
                max_size=500,
                default_ttl=3600  # 1 hour
            )

    def _make_key(self, query: str, **params) -> str:
        """Create cache key from API parameters."""
        # Include query and relevant parameters
        key_parts = [query]

        for param in ['max_results', 'location', 'language']:
            if param in params:
                key_parts.append(f"{param}={params[param]}")

        # Hash the combined key
        key_str = "|".join(str(p) for p in key_parts)
        return f"api:{hashlib.sha256(key_str.encode()).hexdigest()}"

    def get(self, query: str, **params) -> Optional[list]:
        """Get cached API response."""
        key = self._make_key(query, **params)
        return self.cache.get(key)

    def set(self, query: str, results: list, **params):
        """Cache API response."""
        key = self._make_key(query, **params)
        self.cache.set(key, results)

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.cache.get_stats()

    def clear(self):
        """Clear all cached API responses."""
        self.cache.clear()


class QueryCache:
    """Specialized cache for generated dork queries."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize query cache.

        Args:
            cache_dir: Directory for persistent cache (None = memory only)
        """
        if cache_dir:
            self.cache = DiskCache(
                cache_dir / "query_cache",
                max_size=200,
                default_ttl=86400 * 30  # 30 days
            )
        else:
            self.cache = InMemoryCache(
                max_size=100,
                default_ttl=86400  # 24 hours
            )

    def _make_key(self, target_domain: str, category: str, goal: str = "") -> str:
        """Create cache key from query parameters."""
        key_parts = [target_domain, category, goal]
        key_str = "|".join(str(p) for p in key_parts)
        return f"query:{hashlib.sha256(key_str.encode()).hexdigest()}"

    def get(self, target_domain: str, category: str, goal: str = "") -> Optional[list]:
        """Get cached queries."""
        key = self._make_key(target_domain, category, goal)
        return self.cache.get(key)

    def set(self, target_domain: str, category: str, queries: list, goal: str = ""):
        """Cache generated queries."""
        key = self._make_key(target_domain, category, goal)
        self.cache.set(key, queries)

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.cache.get_stats()

    def clear(self):
        """Clear all cached queries."""
        self.cache.clear()


class CacheManager:
    """Central manager for all caches."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Base directory for all caches (None = memory only)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None

        self.llm_cache = LLMCache(self.cache_dir)
        self.api_cache = APICache(self.cache_dir)
        self.query_cache = QueryCache(self.cache_dir)

    def get_global_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        return {
            "llm": self.llm_cache.get_stats().to_dict(),
            "api": self.api_cache.get_stats().to_dict(),
            "query": self.query_cache.get_stats().to_dict()
        }

    def clear_all(self):
        """Clear all caches."""
        self.llm_cache.clear()
        self.api_cache.clear()
        self.query_cache.clear()


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(cache_dir: Optional[Path] = None) -> CacheManager:
    """
    Get global cache manager instance.

    Args:
        cache_dir: Base directory for caches

    Returns:
        CacheManager instance
    """
    global _cache_manager

    if _cache_manager is None:
        # Use .osint85/cache as default if not specified
        if cache_dir is None:
            cache_dir = Path.home() / ".osint85" / "cache"

        _cache_manager = CacheManager(cache_dir)

    return _cache_manager
