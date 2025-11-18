"""Unit tests for performance profiling module."""

import pytest
import time
from pathlib import Path

from osint85.perf import (
    PerformanceProfiler,
    DatabaseProfiler,
    PerformanceStats,
    QueryProfile,
    get_profiler
)


class TestQueryProfile:
    """Test QueryProfile dataclass."""

    def test_complete_calculates_duration(self):
        """Test completing a profile calculates duration."""
        profile = QueryProfile(operation="test", start_time=time.time())

        time.sleep(0.01)
        profile.complete()

        assert profile.end_time is not None
        assert profile.duration is not None
        assert profile.duration > 0


class TestPerformanceProfiler:
    """Test PerformanceProfiler class."""

    def test_profile_context_manager(self):
        """Test profiling with context manager."""
        profiler = PerformanceProfiler()

        with profiler.profile("test.operation"):
            time.sleep(0.01)

        assert len(profiler.profiles) == 1
        assert profiler.profiles[0].operation == "test.operation"
        assert profiler.profiles[0].duration > 0

    def test_profile_with_metadata(self):
        """Test profiling stores metadata."""
        profiler = PerformanceProfiler()

        with profiler.profile("db.query", table="users", action="select"):
            pass

        assert profiler.profiles[0].metadata["table"] == "users"
        assert profiler.profiles[0].metadata["action"] == "select"

    def test_disabled_profiler_no_overhead(self):
        """Test disabled profiler has minimal overhead."""
        profiler = PerformanceProfiler(enabled=False)

        with profiler.profile("test"):
            pass

        assert len(profiler.profiles) == 0

    def test_get_stats(self):
        """Test getting aggregated statistics."""
        profiler = PerformanceProfiler()

        with profiler.profile("db.query"):
            time.sleep(0.01)

        with profiler.profile("llm.call"):
            time.sleep(0.02)

        stats = profiler.get_stats()

        assert stats.total_operations == 2
        assert stats.db_queries == 1
        assert stats.llm_calls == 1
        assert stats.total_duration > 0

    def test_get_slowest_operations(self):
        """Test getting slowest operations."""
        profiler = PerformanceProfiler()

        # Create operations with different durations
        with profiler.profile("fast"):
            time.sleep(0.001)

        with profiler.profile("slow"):
            time.sleep(0.01)

        with profiler.profile("medium"):
            time.sleep(0.005)

        slowest = profiler.get_slowest_operations(limit=2)

        assert len(slowest) == 2
        assert slowest[0].operation == "slow"

    def test_get_operation_summary(self):
        """Test getting operation summary."""
        profiler = PerformanceProfiler()

        # Profile same operation multiple times
        for i in range(3):
            with profiler.profile("db.query"):
                time.sleep(0.001)

        summary = profiler.get_operation_summary()

        assert "db.query" in summary
        assert summary["db.query"]["count"] == 3
        assert "avg_time" in summary["db.query"]

    def test_reset(self):
        """Test resetting profiler."""
        profiler = PerformanceProfiler()

        with profiler.profile("test"):
            pass

        profiler.reset()

        assert len(profiler.profiles) == 0
        assert len(profiler._operation_counts) == 0

    def test_save_to_file(self, temp_dir):
        """Test saving profiling data to file."""
        profiler = PerformanceProfiler()

        with profiler.profile("test"):
            time.sleep(0.01)

        output_file = temp_dir / "profile.json"
        profiler.save_to_file(output_file)

        assert output_file.exists()

        # Verify JSON is valid
        import json
        with open(output_file) as f:
            data = json.load(f)

        assert "stats" in data
        assert "operation_summary" in data


class TestDatabaseProfiler:
    """Test DatabaseProfiler class."""

    def test_get_query_stats(self, test_db_with_data, temp_dir):
        """Test getting database query statistics."""
        test_db, target, queries = test_db_with_data
        db_path = test_db.db_path

        profiler = DatabaseProfiler(str(db_path))
        stats = profiler.get_query_stats()

        assert "targets_count" in stats
        assert "queries_count" in stats
        assert "results_count" in stats
        assert "db_size_mb" in stats
        assert stats["targets_count"] > 0

    def test_analyze_query_performance(self, test_db_with_data):
        """Test analyzing query performance."""
        test_db, target, queries = test_db_with_data
        db_path = test_db.db_path

        profiler = DatabaseProfiler(str(db_path))
        analysis = profiler.analyze_query_performance()

        assert "recommendations" in analysis
        assert isinstance(analysis["recommendations"], list)


class TestPerformanceStats:
    """Test PerformanceStats dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = PerformanceStats(
            total_operations=10,
            total_duration=5.5,
            avg_duration=0.55,
            db_queries=3,
            llm_calls=2
        )

        result = stats.to_dict()

        assert result["total_operations"] == 10
        assert "5.50s" in result["total_duration"]
        assert result["db_queries"] == 3


class TestGlobalProfiler:
    """Test global profiler instance."""

    def test_get_profiler_singleton(self):
        """Test get_profiler returns singleton."""
        p1 = get_profiler()
        p2 = get_profiler()

        assert p1 is p2
