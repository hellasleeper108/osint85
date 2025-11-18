"""Unit tests for cache module."""

import pytest
import time
from pathlib import Path

from osint85.cache import (
    InMemoryCache,
    DiskCache,
    LLMCache,
    APICache,
    QueryCache,
    CacheManager,
    CacheEntry,
    CacheStats
)


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_is_expired_no_ttl(self):
        """Test entry without TTL never expires."""
        entry = CacheEntry(key="test", value="data", created_at=time.time(), ttl=None)
        assert not entry.is_expired()

    def test_is_expired_with_ttl(self):
        """Test entry with TTL expires correctly."""
        # Create entry that expired 2 seconds ago
        entry = CacheEntry(
            key="test",
            value="data",
            created_at=time.time() - 3,
            ttl=1.0
        )
        assert entry.is_expired()

    def test_is_not_expired_with_ttl(self):
        """Test entry with TTL not yet expired."""
        entry = CacheEntry(
            key="test",
            value="data",
            created_at=time.time(),
            ttl=10.0
        )
        assert not entry.is_expired()

    def test_touch_updates_metadata(self):
        """Test touch updates last_accessed and access_count."""
        entry = CacheEntry(key="test", value="data", created_at=time.time())
        initial_accessed = entry.last_accessed
        initial_count = entry.access_count

        time.sleep(0.01)
        entry.touch()

        assert entry.last_accessed > initial_accessed
        assert entry.access_count == initial_count + 1


class TestInMemoryCache:
    """Test InMemoryCache implementation."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = InMemoryCache(max_size=10)
        cache.set("key1", "value1")

        assert cache.get("key1") == "value1"
        assert cache.size() == 1

    def test_get_nonexistent_key(self):
        """Test getting non-existent key returns None."""
        cache = InMemoryCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        """Test entries expire based on TTL."""
        cache = InMemoryCache(default_ttl=0.1)
        cache.set("key1", "value1")

        # Should exist immediately
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired
        assert cache.get("key1") is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = InMemoryCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add key4, should evict key2 (least recently used)
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_delete(self):
        """Test deleting entries."""
        cache = InMemoryCache()
        cache.set("key1", "value1")

        assert cache.delete("key1")
        assert cache.get("key1") is None
        assert not cache.delete("key1")  # Already deleted

    def test_clear(self):
        """Test clearing all entries."""
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.size() == 0
        assert cache.get("key1") is None

    def test_stats_tracking(self):
        """Test cache statistics are tracked correctly."""
        cache = InMemoryCache()

        # Miss
        cache.get("nonexistent")
        assert cache.stats.misses == 1

        # Set and hit
        cache.set("key1", "value1")
        cache.get("key1")
        assert cache.stats.hits == 1

        # Hit rate
        assert cache.stats.hit_rate == 50.0  # 1 hit, 1 miss


class TestDiskCache:
    """Test DiskCache implementation."""

    def test_set_and_get(self, test_cache_dir):
        """Test basic disk cache operations."""
        cache = DiskCache(test_cache_dir, max_size=10)
        cache.set("key1", {"data": "value1"})

        result = cache.get("key1")
        assert result == {"data": "value1"}

    def test_persistence(self, test_cache_dir):
        """Test cache persists across instances."""
        cache1 = DiskCache(test_cache_dir)
        cache1.set("key1", "value1")

        # Create new instance
        cache2 = DiskCache(test_cache_dir)
        assert cache2.get("key1") == "value1"

    def test_ttl_expiration(self, test_cache_dir):
        """Test disk cache TTL expiration."""
        cache = DiskCache(test_cache_dir, default_ttl=0.1)
        cache.set("key1", "value1")

        # Should exist immediately
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired
        assert cache.get("key1") is None

    def test_delete(self, test_cache_dir):
        """Test deleting disk cache entries."""
        cache = DiskCache(test_cache_dir)
        cache.set("key1", "value1")

        assert cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self, test_cache_dir):
        """Test clearing all disk cache entries."""
        cache = DiskCache(test_cache_dir)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.size() == 0
        assert cache.get("key1") is None


class TestLLMCache:
    """Test LLMCache specialized cache."""

    def test_cache_by_model_and_prompt(self, test_cache_dir):
        """Test LLM responses are cached by model and prompt."""
        cache = LLMCache(test_cache_dir)

        # Cache response
        cache.set("gpt-4", "What is 2+2?", "4")

        # Should retrieve same response
        result = cache.get("gpt-4", "What is 2+2?")
        assert result == "4"

        # Different prompt should miss
        result = cache.get("gpt-4", "What is 3+3?")
        assert result is None

        # Different model should miss
        result = cache.get("gpt-3.5", "What is 2+2?")
        assert result is None

    def test_cache_with_parameters(self, test_cache_dir):
        """Test LLM cache considers parameters in key."""
        cache = LLMCache(test_cache_dir)

        # Cache with temperature 0.7
        cache.set("gpt-4", "test", "response1", temperature=0.7)

        # Same temperature should hit
        assert cache.get("gpt-4", "test", temperature=0.7) == "response1"

        # Different temperature should miss
        assert cache.get("gpt-4", "test", temperature=0.9) is None

    def test_clear(self, test_cache_dir):
        """Test clearing LLM cache."""
        cache = LLMCache(test_cache_dir)
        cache.set("gpt-4", "test", "response")

        cache.clear()

        assert cache.get("gpt-4", "test") is None


class TestAPICache:
    """Test APICache specialized cache."""

    def test_cache_by_query(self, test_cache_dir):
        """Test API responses are cached by query."""
        cache = APICache(test_cache_dir)

        results = [{"url": "https://example.com", "title": "Test"}]
        cache.set("site:example.com", results)

        cached = cache.get("site:example.com")
        assert cached == results

    def test_cache_with_parameters(self, test_cache_dir):
        """Test API cache considers parameters."""
        cache = APICache(test_cache_dir)

        results = [{"url": "https://example.com"}]
        cache.set("test query", results, max_results=10)

        # Same params should hit
        assert cache.get("test query", max_results=10) == results

        # Different params should miss
        assert cache.get("test query", max_results=20) is None


class TestQueryCache:
    """Test QueryCache specialized cache."""

    def test_cache_by_target_and_category(self, test_cache_dir):
        """Test queries are cached by target domain and category."""
        cache = QueryCache(test_cache_dir)

        queries = [
            {"query": "site:example.com filetype:env", "description": "Find env files"}
        ]

        cache.set("example.com", "exposed_files", queries)

        cached = cache.get("example.com", "exposed_files")
        assert cached == queries

    def test_cache_with_goal(self, test_cache_dir):
        """Test query cache considers goal parameter."""
        cache = QueryCache(test_cache_dir)

        queries = [{"query": "test"}]
        cache.set("example.com", "exposed_files", queries, goal="find configs")

        # Same goal should hit
        assert cache.get("example.com", "exposed_files", goal="find configs") == queries

        # Different goal should miss
        assert cache.get("example.com", "exposed_files", goal="find backups") is None


class TestCacheManager:
    """Test CacheManager orchestration."""

    def test_initialization(self, test_cache_dir):
        """Test cache manager initializes all caches."""
        manager = CacheManager(test_cache_dir)

        assert manager.llm_cache is not None
        assert manager.api_cache is not None
        assert manager.query_cache is not None

    def test_global_stats(self, test_cache_dir):
        """Test getting global cache statistics."""
        manager = CacheManager(test_cache_dir)

        # Add some cache entries
        manager.llm_cache.set("gpt-4", "test", "response")
        manager.api_cache.set("query", [{"url": "test"}])

        # Get stats
        stats = manager.get_global_stats()

        assert "llm" in stats
        assert "api" in stats
        assert "query" in stats

    def test_clear_all(self, test_cache_dir):
        """Test clearing all caches."""
        manager = CacheManager(test_cache_dir)

        # Add entries to all caches
        manager.llm_cache.set("gpt-4", "test", "response")
        manager.api_cache.set("query", [{"url": "test"}])
        manager.query_cache.set("example.com", "category", [{"query": "test"}])

        # Clear all
        manager.clear_all()

        # Verify all caches are empty
        assert manager.llm_cache.get("gpt-4", "test") is None
        assert manager.api_cache.get("query") is None
        assert manager.query_cache.get("example.com", "category") is None


class TestCacheStats:
    """Test CacheStats dataclass."""

    def test_hit_rate_calculation(self):
        """Test hit rate percentage calculation."""
        stats = CacheStats(hits=7, misses=3)
        assert stats.hit_rate == 70.0

    def test_hit_rate_no_operations(self):
        """Test hit rate when no operations."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = CacheStats(
            hits=10,
            misses=5,
            evictions=2,
            total_size=100
        )

        result = stats.to_dict()

        assert result["hits"] == 10
        assert result["misses"] == 5
        assert "66.7%" in result["hit_rate"]
