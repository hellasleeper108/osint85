"""Unit tests for database module."""

import pytest
from datetime import datetime

from osint85.database import Database, Target, Query, Result


class TestDatabase:
    """Test Database class."""

    def test_initialization(self, temp_dir):
        """Test database initialization creates schema."""
        db_path = temp_dir / "test.db"
        db = Database(str(db_path))

        assert db_path.exists()
        assert db.conn is not None

        db.close()

    def test_schema_version(self, test_db):
        """Test schema version is tracked."""
        assert test_db.SCHEMA_VERSION == 3

    def test_close(self, test_db):
        """Test closing database connection."""
        test_db.close()
        assert test_db.conn is None


class TestTargetOperations:
    """Test Target CRUD operations."""

    def test_create_target(self, test_db):
        """Test creating a new target."""
        target = test_db.create_target(
            name="Test Target",
            primary_domain="example.com",
            notes="Test notes",
            scope="*.example.com"
        )

        assert target.id is not None
        assert target.name == "Test Target"
        assert target.primary_domain == "example.com"
        assert target.notes == "Test notes"
        assert target.scope == "*.example.com"
        assert target.created_at is not None

    def test_get_target(self, test_db):
        """Test retrieving a target by ID."""
        created = test_db.create_target(
            name="Test",
            primary_domain="test.com"
        )

        retrieved = test_db.get_target(created.id)

        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.primary_domain == created.primary_domain

    def test_get_nonexistent_target(self, test_db):
        """Test getting non-existent target raises ValueError."""
        with pytest.raises(ValueError, match="Target.*not found"):
            test_db.get_target(9999)

    def test_list_targets(self, test_db):
        """Test listing all targets."""
        test_db.create_target("Target 1", "example1.com")
        test_db.create_target("Target 2", "example2.com")

        targets = sorted(test_db.list_targets(), key=lambda t: t.name)

        assert len(targets) == 2
        assert targets[0].name == "Target 1"
        assert targets[1].name == "Target 2"

    def test_list_targets_empty(self, test_db):
        """Test listing targets when none exist."""
        targets = test_db.list_targets()
        assert targets == []


class TestQueryOperations:
    """Test Query CRUD operations."""

    def test_save_queries(self, test_db):
        """Test saving multiple queries."""
        target = test_db.create_target("Test", "test.com")

        queries_data = [
            {
                "category": "exposed_files",
                "risk_level": "high",
                "description": "Find configs",
                "query": "site:test.com filetype:env"
            },
            {
                "category": "subdomains",
                "risk_level": "low",
                "description": "Find subdomains",
                "query": "site:*.test.com"
            }
        ]

        queries = test_db.save_queries(target.id, queries_data)

        assert len(queries) == 2
        assert queries[0].category == "exposed_files"
        assert queries[1].category == "subdomains"

    def test_get_query(self, test_db):
        """Test retrieving a query by ID."""
        target = test_db.create_target("Test", "test.com")
        queries = test_db.save_queries(target.id, [{
            "category": "test",
            "risk_level": "medium",
            "description": "Test query",
            "query": "site:test.com"
        }])

        retrieved = test_db.get_query(queries[0].id)

        assert retrieved.id == queries[0].id
        assert retrieved.query == "site:test.com"

    def test_get_queries_by_target(self, test_db):
        """Test getting all queries for a target."""
        target = test_db.create_target("Test", "test.com")
        test_db.save_queries(target.id, [
            {"category": "cat1", "risk_level": "low", "description": "Q1", "query": "q1"},
            {"category": "cat2", "risk_level": "high", "description": "Q2", "query": "q2"}
        ])

        queries = test_db.list_queries(target.id)

        assert len(queries) == 2

    def test_get_queries_by_target_enabled_only(self, test_db):
        """Test filtering enabled queries only."""
        target = test_db.create_target("Test", "test.com")
        queries = test_db.save_queries(target.id, [
            {"category": "cat1", "risk_level": "low", "description": "Q1", "query": "q1"},
            {"category": "cat2", "risk_level": "high", "description": "Q2", "query": "q2"}
        ])

        # Disable one query
        test_db.toggle_query(queries[0].id, False)

        enabled_queries = test_db.get_enabled_queries(target.id)

        assert len(enabled_queries) == 1
        assert enabled_queries[0].id == queries[1].id

    def test_toggle_query(self, test_db):
        """Test toggling query enabled state."""
        target = test_db.create_target("Test", "test.com")
        queries = test_db.save_queries(target.id, [{
            "category": "test",
            "risk_level": "low",
            "description": "Test",
            "query": "test"
        }])

        # Disable
        test_db.toggle_query(queries[0].id, False)
        query = test_db.get_query(queries[0].id)
        assert not query.enabled

        # Enable
        test_db.toggle_query(queries[0].id, True)
        query = test_db.get_query(queries[0].id)
        assert query.enabled


class TestResultOperations:
    """Test Result CRUD operations."""

    def test_save_result(self, test_db):
        """Test saving a result."""
        target = test_db.create_target("Test", "test.com")
        queries = test_db.save_queries(target.id, [{
            "category": "test",
            "risk_level": "low",
            "description": "Test",
            "query": "test"
        }])

        result = test_db.save_result(
            query_id=queries[0].id,
            url="https://test.com/page",
            title="Test Page",
            snippet="Test snippet",
            source_engine="mock",
            tags="tag1,tag2"
        )

        assert result.id is not None

    def test_save_duplicate_result_updates(self, test_db):
        """Test saving duplicate URL updates existing result."""
        target = test_db.create_target("Test", "test.com")
        queries = test_db.save_queries(target.id, [{
            "category": "test",
            "risk_level": "low",
            "description": "Test",
            "query": "test"
        }])

        # Save first time
        r1 = test_db.save_result(
            query_id=queries[0].id,
            url="https://test.com/page",
            title="Title 1",
            snippet="Snippet 1"
        )

        # Save same URL again
        r2 = test_db.save_result(
            query_id=queries[0].id,
            url="https://test.com/page",
            title="Title 2",
            snippet="Snippet 2"
        )

        # Should return same ID (update, not insert)
        assert r1.id == r2.id

        # Verify only one result exists
        results = test_db.get_results_by_query(queries[0].id)
        assert len(results) == 1

    def test_get_results_by_query(self, test_db):
        """Test getting results for a query."""
        target = test_db.create_target("Test", "test.com")
        queries = test_db.save_queries(target.id, [{
            "category": "test",
            "risk_level": "low",
            "description": "Test",
            "query": "test"
        }])

        # Add results
        for i in range(3):
            test_db.save_result(
                query_id=queries[0].id,
                url=f"https://test.com/page{i}",
                title=f"Page {i}"
            )

        results = test_db.get_results_by_query(queries[0].id)

        assert len(results) == 3
        assert all(r.query_id == queries[0].id for r in results)

    def test_get_all_results(self, test_db_with_data):
        """Test getting all results for a target."""
        test_db, target, queries = test_db_with_data

        results = test_db.get_all_results(target.id)

        assert len(results) > 0
        assert all(hasattr(r, 'url') for r in results)

    def test_get_all_results_by_category(self, test_db_with_data):
        """Test filtering results by category."""
        test_db, target, queries = test_db_with_data

        # Get category from first query
        category = queries[0].category

        results = test_db.get_all_results(target.id, category=category)

        assert len(results) > 0

    def test_mark_as_duplicate(self, test_db):
        """Test marking a result as duplicate."""
        target = test_db.create_target("Test", "test.com")
        queries = test_db.save_queries(target.id, [{
            "category": "test",
            "risk_level": "low",
            "description": "Test",
            "query": "test"
        }])

        # Create two results
        r1 = test_db.save_result(queries[0].id, "https://test.com/1", "Page 1")
        r2 = test_db.save_result(queries[0].id, "https://test.com/2", "Page 2")

        # Mark id2 as duplicate of id1
        test_db.mark_as_duplicate(r2.id, r1.id, similarity_score=95.5)

        # Verify
        results = test_db.get_results_by_query(queries[0].id)
        duplicate_result = next(r for r in results if r.id == r2.id)

        assert duplicate_result.is_duplicate
        assert duplicate_result.duplicate_of_id == r1.id
        assert duplicate_result.similarity_score == 95.5

    def test_delete_result(self, test_db):
        """Test deleting a result."""
        target = test_db.create_target("Test", "test.com")
        queries = test_db.save_queries(target.id, [{
            "category": "test",
            "risk_level": "low",
            "description": "Test",
            "query": "test"
        }])

        result = test_db.save_result(queries[0].id, "https://test.com", "Test")

        # Delete
        test_db.delete_result(result.id)

        # Verify deleted
        results = test_db.get_results_by_query(queries[0].id)
        assert len(results) == 0


class TestDatabaseMigrations:
    """Test database schema migrations."""

    def test_migration_adds_dedup_columns(self, temp_dir):
        """Test migration adds deduplication columns."""
        db_path = temp_dir / "test.db"
        db = Database(str(db_path))

        # Check columns exist
        cursor = db.conn.cursor()
        cursor.execute("PRAGMA table_info(results)")
        columns = [row[1] for row in cursor.fetchall()]

        assert "is_duplicate" in columns
        assert "duplicate_of_id" in columns
        assert "similarity_score" in columns

        db.close()

    def test_migration_adds_indexes(self, temp_dir):
        """Test migration creates performance indexes."""
        db_path = temp_dir / "test.db"
        db = Database(str(db_path))

        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        # Check key indexes exist
        assert "idx_queries_target" in indexes
        assert "idx_queries_category" in indexes
        assert "idx_results_query" in indexes
        assert "idx_results_url" in indexes

        db.close()
