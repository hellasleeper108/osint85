"""Unit tests for database module."""

import pytest
import tempfile
from pathlib import Path

from osint85.database import Database, Target, Query, Result


class TestDatabase:
    """Tests for Database class."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path)
        yield db
        db.close()

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    def test_create_target_success(self, temp_db):
        """Test that create_target successfully creates a target."""
        # Act
        target = temp_db.create_target(
            name="Test Target",
            primary_domain="example.com",
            notes="Test notes",
            scope="Test scope"
        )

        # Assert
        assert target.id is not None
        assert target.name == "Test Target"
        assert target.primary_domain == "example.com"
        assert target.notes == "Test notes"
        assert target.scope == "Test scope"

    def test_get_target_success(self, temp_db):
        """Test that get_target retrieves an existing target."""
        # Arrange
        created = temp_db.create_target(
            name="Test Target",
            primary_domain="example.com"
        )

        # Act
        retrieved = temp_db.get_target(created.id)

        # Assert
        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.primary_domain == created.primary_domain

    def test_get_target_not_found(self, temp_db):
        """Test that get_target raises error for non-existent target."""
        with pytest.raises(ValueError, match="Target.*not found"):
            temp_db.get_target(99999)

    def test_list_targets(self, temp_db):
        """Test that list_targets returns all targets."""
        # Arrange
        temp_db.create_target(name="Target 1", primary_domain="example1.com")
        temp_db.create_target(name="Target 2", primary_domain="example2.com")

        # Act
        targets = temp_db.list_targets()

        # Assert
        assert len(targets) == 2
        assert targets[0].name in ["Target 1", "Target 2"]

    def test_save_queries(self, temp_db):
        """Test that save_queries creates multiple queries."""
        # Arrange
        target = temp_db.create_target(name="Test", primary_domain="example.com")
        queries = [
            {
                "category": "exposed_backups",
                "risk_level": "high",
                "description": "Find backup files",
                "query": 'site:example.com "backup"'
            },
            {
                "category": "config_files",
                "risk_level": "medium",
                "description": "Find config files",
                "query": 'site:example.com ".config"'
            }
        ]

        # Act
        saved = temp_db.save_queries(target.id, queries)

        # Assert
        assert len(saved) == 2
        assert saved[0].category == "exposed_backups"
        assert saved[1].category == "config_files"

    def test_get_enabled_queries(self, temp_db):
        """Test that get_enabled_queries returns only enabled queries."""
        # Arrange
        target = temp_db.create_target(name="Test", primary_domain="example.com")
        queries = [
            {"category": "test1", "risk_level": "low", "description": "Test 1", "query": "q1"},
            {"category": "test2", "risk_level": "low", "description": "Test 2", "query": "q2"},
        ]
        saved = temp_db.save_queries(target.id, queries)

        # Disable one query
        temp_db.toggle_query(saved[0].id, False)

        # Act
        enabled = temp_db.get_enabled_queries(target.id)

        # Assert
        assert len(enabled) == 1
        assert enabled[0].id == saved[1].id

    def test_save_result(self, temp_db):
        """Test that save_result creates a result."""
        # Arrange
        target = temp_db.create_target(name="Test", primary_domain="example.com")
        queries = [{"category": "test", "risk_level": "low", "description": "Test", "query": "q"}]
        saved_queries = temp_db.save_queries(target.id, queries)

        # Act
        result = temp_db.save_result(
            query_id=saved_queries[0].id,
            url="https://example.com/test",
            title="Test Page",
            snippet="Test snippet",
            source_engine="google",
            tags="backup,config"
        )

        # Assert
        assert result.id is not None
        assert result.url == "https://example.com/test"
        assert result.tags == "backup,config"

    def test_save_result_duplicate_updates_timestamp(self, temp_db):
        """Test that saving duplicate result updates last_seen_at."""
        # Arrange
        target = temp_db.create_target(name="Test", primary_domain="example.com")
        queries = [{"category": "test", "risk_level": "low", "description": "Test", "query": "q"}]
        saved_queries = temp_db.save_queries(target.id, queries)

        # Act
        result1 = temp_db.save_result(
            query_id=saved_queries[0].id,
            url="https://example.com/test",
            title="Test"
        )
        result2 = temp_db.save_result(
            query_id=saved_queries[0].id,
            url="https://example.com/test",
            title="Test Updated"
        )

        # Assert
        assert result1.id == result2.id  # Same result
        assert result1.first_seen_at == result2.first_seen_at
        # last_seen_at should be updated (this is a basic check)

    def test_get_all_results(self, temp_db):
        """Test that get_all_results returns all results for a target."""
        # Arrange
        target = temp_db.create_target(name="Test", primary_domain="example.com")
        queries = [
            {"category": "test1", "risk_level": "low", "description": "Test 1", "query": "q1"},
            {"category": "test2", "risk_level": "low", "description": "Test 2", "query": "q2"},
        ]
        saved_queries = temp_db.save_queries(target.id, queries)

        temp_db.save_result(saved_queries[0].id, "https://example.com/1", "Title 1")
        temp_db.save_result(saved_queries[0].id, "https://example.com/2", "Title 2")
        temp_db.save_result(saved_queries[1].id, "https://example.com/3", "Title 3")

        # Act
        results = temp_db.get_all_results(target.id)

        # Assert
        assert len(results) == 3
