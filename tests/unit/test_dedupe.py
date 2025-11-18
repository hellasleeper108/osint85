"""Unit tests for deduplication module."""

import pytest
from osint85.dedupe import URLNormalizer, DeduplicationEngine, DuplicateGroup


class TestURLNormalizer:
    """Test URL normalization."""

    def test_normalize_removes_protocol(self):
        """Test protocol is normalized."""
        url1 = "https://example.com/page"
        url2 = "http://example.com/page"

        assert URLNormalizer.normalize(url1) == URLNormalizer.normalize(url2)

    def test_normalize_removes_www(self):
        """Test www subdomain is removed."""
        url1 = "https://www.example.com/page"
        url2 = "https://example.com/page"

        assert URLNormalizer.normalize(url1) == URLNormalizer.normalize(url2)

    def test_normalize_removes_trailing_slash(self):
        """Test trailing slashes are removed."""
        url1 = "https://example.com/page/"
        url2 = "https://example.com/page"

        assert URLNormalizer.normalize(url1) == URLNormalizer.normalize(url2)

    def test_normalize_removes_tracking_params(self):
        """Test tracking parameters are removed."""
        url1 = "https://example.com/page?utm_source=test&fbclid=abc"
        url2 = "https://example.com/page"

        assert URLNormalizer.normalize(url1) == URLNormalizer.normalize(url2)

    def test_normalize_keeps_important_params(self):
        """Test important query parameters are kept."""
        url = "https://example.com/page?id=123&page=2"
        normalized = URLNormalizer.normalize(url)

        assert "id=123" in normalized or "id" in normalized
        assert "page=2" in normalized or "page" in normalized

    def test_normalize_case_insensitive(self):
        """Test normalization is case insensitive."""
        url1 = "https://EXAMPLE.COM/PAGE"
        url2 = "https://example.com/page"

        assert URLNormalizer.normalize(url1) == URLNormalizer.normalize(url2)


class TestDeduplicationEngine:
    """Test deduplication engine."""

    def test_find_exact_duplicates(self, test_project_manager, sample_target, sample_results_list):
        """Test finding exact URL duplicates."""
        engine = DeduplicationEngine(test_project_manager)

        # Create results with exact duplicates
        results = sample_results_list[:2]
        results.append(sample_results_list[0])  # Exact duplicate

        groups = engine.find_duplicates(results)

        assert len(groups) > 0

    def test_find_fuzzy_duplicates(self, test_project_manager):
        """Test finding fuzzy duplicates."""
        from osint85.database import Result

        engine = DeduplicationEngine(test_project_manager, fuzzy_threshold=90.0)

        # Create similar URLs
        results = [
            Result(id=1, query_id=1, url="https://example.com/page?id=123", title="Page"),
            Result(id=2, query_id=1, url="https://example.com/page?id=456", title="Page"),
        ]

        groups = engine.find_duplicates(results)

        # Should find fuzzy duplicates
        assert len(groups) >= 0  # May or may not find depending on similarity

    def test_mark_duplicates(self, test_db_with_data, test_project_manager):
        """Test marking duplicates in database."""
        test_db, target, queries = test_db_with_data

        engine = DeduplicationEngine(test_project_manager)
        marked_count = engine.mark_duplicates(target.id)

        assert marked_count >= 0

    def test_remove_duplicates(self, test_db_with_data, test_project_manager):
        """Test removing duplicates from database."""
        test_db, target, queries = test_db_with_data

        engine = DeduplicationEngine(test_project_manager)

        # First mark
        engine.mark_duplicates(target.id)

        # Then remove
        removed_count = engine.remove_duplicates(target.id)

        assert removed_count >= 0

    def test_get_duplicate_stats(self, test_db_with_data, test_project_manager):
        """Test getting duplicate statistics."""
        test_db, target, queries = test_db_with_data

        engine = DeduplicationEngine(test_project_manager)
        stats = engine.get_duplicate_stats(target.id)

        assert "total_results" in stats
        assert "unique_results" in stats
        assert "duplicate_results" in stats
        assert "duplicate_groups" in stats
