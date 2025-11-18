"""
Performance profiling and monitoring for OSINT-85.

Tracks query times, LLM usage, cache performance, and system metrics.
"""

import time
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from .cache import get_cache_manager


@dataclass
class QueryProfile:
    """Profile data for a single operation."""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self):
        """Mark operation as complete and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    total_operations: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    avg_duration: float = 0.0

    # Operation-specific stats
    db_queries: int = 0
    db_time: float = 0.0
    llm_calls: int = 0
    llm_time: float = 0.0
    api_calls: int = 0
    api_time: float = 0.0

    # Cache stats
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_operations": self.total_operations,
            "total_duration": f"{self.total_duration:.2f}s",
            "avg_duration": f"{self.avg_duration:.3f}s",
            "min_duration": f"{self.min_duration:.3f}s" if self.min_duration != float('inf') else "N/A",
            "max_duration": f"{self.max_duration:.3f}s",
            "db_queries": self.db_queries,
            "db_time": f"{self.db_time:.2f}s",
            "llm_calls": self.llm_calls,
            "llm_time": f"{self.llm_time:.2f}s",
            "api_calls": self.api_calls,
            "api_time": f"{self.api_time:.2f}s",
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": f"{self.cache_hit_rate:.1f}%"
        }


class PerformanceProfiler:
    """Performance profiler for tracking operations."""

    def __init__(self, enabled: bool = True):
        """
        Initialize profiler.

        Args:
            enabled: Whether profiling is enabled
        """
        self.enabled = enabled
        self.profiles: List[QueryProfile] = []
        self._operation_counts: Dict[str, int] = defaultdict(int)
        self._operation_times: Dict[str, List[float]] = defaultdict(list)

    @contextmanager
    def profile(self, operation: str, **metadata):
        """
        Context manager for profiling an operation.

        Args:
            operation: Name of the operation (e.g., "db.query", "llm.generate")
            **metadata: Additional metadata to store

        Example:
            with profiler.profile("db.query", table="results"):
                results = db.get_results()
        """
        if not self.enabled:
            yield
            return

        profile = QueryProfile(
            operation=operation,
            start_time=time.time(),
            metadata=metadata
        )

        try:
            yield profile
        finally:
            profile.complete()
            self.profiles.append(profile)
            self._operation_counts[operation] += 1
            if profile.duration:
                self._operation_times[operation].append(profile.duration)

    def get_stats(self) -> PerformanceStats:
        """Get aggregated performance statistics."""
        stats = PerformanceStats()

        if not self.profiles:
            return stats

        # Calculate overall stats
        durations = [p.duration for p in self.profiles if p.duration is not None]
        stats.total_operations = len(self.profiles)
        stats.total_duration = sum(durations)
        stats.avg_duration = stats.total_duration / len(durations) if durations else 0.0
        stats.min_duration = min(durations) if durations else 0.0
        stats.max_duration = max(durations) if durations else 0.0

        # Calculate operation-specific stats
        for operation, times in self._operation_times.items():
            if operation.startswith("db."):
                stats.db_queries += len(times)
                stats.db_time += sum(times)
            elif operation.startswith("llm."):
                stats.llm_calls += len(times)
                stats.llm_time += sum(times)
            elif operation.startswith("api."):
                stats.api_calls += len(times)
                stats.api_time += sum(times)

        # Get cache stats
        cache_manager = get_cache_manager()
        cache_stats = cache_manager.get_global_stats()

        # Aggregate cache stats
        for cache_type, cache_data in cache_stats.items():
            stats.cache_hits += cache_data.get("hits", 0)
            stats.cache_misses += cache_data.get("misses", 0)

        # Calculate hit rate
        total_cache_ops = stats.cache_hits + stats.cache_misses
        if total_cache_ops > 0:
            stats.cache_hit_rate = (stats.cache_hits / total_cache_ops) * 100

        return stats

    def get_slowest_operations(self, limit: int = 10) -> List[QueryProfile]:
        """
        Get slowest operations.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of QueryProfile objects sorted by duration (slowest first)
        """
        sorted_profiles = sorted(
            [p for p in self.profiles if p.duration is not None],
            key=lambda p: p.duration,
            reverse=True
        )
        return sorted_profiles[:limit]

    def get_operation_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summary statistics grouped by operation type.

        Returns:
            Dictionary mapping operation names to their stats
        """
        summary = {}

        for operation, times in self._operation_times.items():
            if times:
                summary[operation] = {
                    "count": len(times),
                    "total_time": sum(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times)
                }

        return summary

    def reset(self):
        """Reset all profiling data."""
        self.profiles.clear()
        self._operation_counts.clear()
        self._operation_times.clear()

    def save_to_file(self, filepath: Path):
        """
        Save profiling data to JSON file.

        Args:
            filepath: Path to save file
        """
        import json

        data = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.get_stats().to_dict(),
            "operation_summary": self.get_operation_summary(),
            "slowest_operations": [
                {
                    "operation": p.operation,
                    "duration": f"{p.duration:.3f}s" if p.duration else "N/A",
                    "metadata": p.metadata
                }
                for p in self.get_slowest_operations(20)
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


class DatabaseProfiler:
    """Specialized profiler for database operations."""

    def __init__(self, db_path: str):
        """
        Initialize database profiler.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)

    def get_query_stats(self) -> Dict[str, Any]:
        """Get database query statistics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        stats = {}

        # Count records in each table
        tables = ["targets", "queries", "results"]
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]

        # Database file size
        stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0

        # Index usage (requires SQLite 3.16+)
        try:
            cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index'")
            stats["indexes"] = [{"name": row[0], "table": row[1]} for row in cursor.fetchall()]
            stats["index_count"] = len(stats["indexes"])
        except Exception:
            stats["indexes"] = []
            stats["index_count"] = 0

        # Table sizes (approximate)
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*), AVG(LENGTH(*))*COUNT(*) FROM {table}")
                row = cursor.fetchone()
                if row and row[1]:
                    stats[f"{table}_size_kb"] = row[1] / 1024
            except Exception:
                stats[f"{table}_size_kb"] = 0

        conn.close()
        return stats

    def analyze_query_performance(self) -> Dict[str, Any]:
        """Analyze slow queries and suggest optimizations."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        analysis = {
            "recommendations": [],
            "index_usage": {},
            "table_scans": []
        }

        # Check for missing indexes on foreign keys
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index'
        """)
        existing_indexes = {row[0] for row in cursor.fetchall()}

        # Expected indexes
        expected = {
            "idx_queries_target", "idx_queries_category",
            "idx_queries_target_category", "idx_results_query",
            "idx_results_url", "idx_results_duplicate"
        }

        missing = expected - existing_indexes
        if missing:
            analysis["recommendations"].append(
                f"Missing indexes: {', '.join(missing)}"
            )

        # Check table sizes and recommend partitioning if needed
        cursor.execute("SELECT COUNT(*) FROM results")
        result_count = cursor.fetchone()[0]

        if result_count > 100000:
            analysis["recommendations"].append(
                f"Large results table ({result_count} rows). Consider archiving old results."
            )

        conn.close()
        return analysis


# Global profiler instance
_profiler: Optional[PerformanceProfiler] = None


def get_profiler(enabled: bool = True) -> PerformanceProfiler:
    """
    Get global profiler instance.

    Args:
        enabled: Whether profiling is enabled

    Returns:
        PerformanceProfiler instance
    """
    global _profiler

    if _profiler is None:
        _profiler = PerformanceProfiler(enabled=enabled)

    return _profiler


def enable_profiling():
    """Enable global profiling."""
    profiler = get_profiler()
    profiler.enabled = True


def disable_profiling():
    """Disable global profiling."""
    profiler = get_profiler()
    profiler.enabled = False


def get_performance_report() -> Dict[str, Any]:
    """
    Get comprehensive performance report.

    Returns:
        Dictionary with performance metrics
    """
    profiler = get_profiler()
    cache_manager = get_cache_manager()

    return {
        "profiler": profiler.get_stats().to_dict(),
        "operation_summary": profiler.get_operation_summary(),
        "cache": cache_manager.get_global_stats(),
        "slowest_operations": [
            {
                "operation": p.operation,
                "duration": f"{p.duration:.3f}s" if p.duration else "N/A",
                "metadata": p.metadata
            }
            for p in profiler.get_slowest_operations(10)
        ]
    }
