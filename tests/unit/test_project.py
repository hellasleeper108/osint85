"""Unit tests for project manager module."""

import pytest
import tempfile
from pathlib import Path

from osint85.project import ProjectManager
from osint85.database import Target


class TestProjectManager:
    """Tests for ProjectManager class."""

    @pytest.fixture
    def temp_pm(self):
        """Create temporary project manager."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        pm = ProjectManager(db_path)
        yield pm
        pm.close()

        Path(db_path).unlink(missing_ok=True)

    def test_create_project(self, temp_pm):
        """Test that create_project creates a new project."""
        # Act
        project = temp_pm.create_project(
            name="Test Project",
            domain="example.com",
            notes="Test notes",
            scope="Test scope"
        )

        # Assert
        assert project.id is not None
        assert project.name == "Test Project"
        assert project.primary_domain == "example.com"

    def test_get_project(self, temp_pm):
        """Test that get_project retrieves existing project."""
        # Arrange
        created = temp_pm.create_project("Test", "example.com")

        # Act
        retrieved = temp_pm.get_project(created.id)

        # Assert
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    def test_list_projects(self, temp_pm):
        """Test that list_projects returns all projects."""
        # Arrange
        temp_pm.create_project("Project 1", "example1.com")
        temp_pm.create_project("Project 2", "example2.com")

        # Act
        projects = temp_pm.list_projects()

        # Assert
        assert len(projects) == 2

    def test_save_queries(self, temp_pm):
        """Test that save_queries saves multiple queries."""
        # Arrange
        project = temp_pm.create_project("Test", "example.com")
        queries = [
            {
                "category": "test",
                "risk_level": "low",
                "description": "Test query",
                "query": "test"
            }
        ]

        # Act
        saved = temp_pm.save_queries(project.id, queries)

        # Assert
        assert len(saved) == 1
        assert saved[0].category == "test"

    def test_get_enabled_queries(self, temp_pm):
        """Test that get_enabled_queries returns only enabled queries."""
        # Arrange
        project = temp_pm.create_project("Test", "example.com")
        queries = [
            {"category": "test1", "risk_level": "low", "description": "Q1", "query": "q1"},
            {"category": "test2", "risk_level": "low", "description": "Q2", "query": "q2"},
        ]
        saved = temp_pm.save_queries(project.id, queries)
        temp_pm.toggle_query(saved[0].id, False)

        # Act
        enabled = temp_pm.get_enabled_queries(project.id)

        # Assert
        assert len(enabled) == 1
        assert enabled[0].id == saved[1].id

    def test_list_queries(self, temp_pm):
        """Test that list_queries returns all queries."""
        # Arrange
        project = temp_pm.create_project("Test", "example.com")
        queries = [
            {"category": "test1", "risk_level": "low", "description": "Q1", "query": "q1"},
            {"category": "test2", "risk_level": "low", "description": "Q2", "query": "q2"},
        ]
        temp_pm.save_queries(project.id, queries)

        # Act
        all_queries = temp_pm.list_queries(project.id)

        # Assert
        assert len(all_queries) == 2

    def test_toggle_query(self, temp_pm):
        """Test that toggle_query enables/disables queries."""
        # Arrange
        project = temp_pm.create_project("Test", "example.com")
        queries = [{"category": "test", "risk_level": "low", "description": "Q", "query": "q"}]
        saved = temp_pm.save_queries(project.id, queries)

        # Act
        temp_pm.toggle_query(saved[0].id, False)
        disabled = temp_pm.get_enabled_queries(project.id)

        temp_pm.toggle_query(saved[0].id, True)
        enabled = temp_pm.get_enabled_queries(project.id)

        # Assert
        assert len(disabled) == 0
        assert len(enabled) == 1

    def test_save_result(self, temp_pm):
        """Test that save_result saves a result."""
        # Arrange
        project = temp_pm.create_project("Test", "example.com")
        queries = [{"category": "test", "risk_level": "low", "description": "Q", "query": "q"}]
        saved_queries = temp_pm.save_queries(project.id, queries)

        # Act
        result = temp_pm.save_result(
            query_id=saved_queries[0].id,
            url="https://example.com/test",
            title="Test Page",
            snippet="Test snippet",
            source_engine="google",
            tags="test,tag"
        )

        # Assert
        assert result.id is not None
        assert result.url == "https://example.com/test"

    def test_get_results_by_query(self, temp_pm):
        """Test that get_results_by_query returns results for a query."""
        # Arrange
        project = temp_pm.create_project("Test", "example.com")
        queries = [{"category": "test", "risk_level": "low", "description": "Q", "query": "q"}]
        saved_queries = temp_pm.save_queries(project.id, queries)
        temp_pm.save_result(saved_queries[0].id, "https://example.com/1", "Title 1")
        temp_pm.save_result(saved_queries[0].id, "https://example.com/2", "Title 2")

        # Act
        results = temp_pm.get_results_by_query(saved_queries[0].id)

        # Assert
        assert len(results) == 2

    def test_get_all_results(self, temp_pm):
        """Test that get_all_results returns all results for a project."""
        # Arrange
        project = temp_pm.create_project("Test", "example.com")
        queries = [
            {"category": "test1", "risk_level": "low", "description": "Q1", "query": "q1"},
            {"category": "test2", "risk_level": "low", "description": "Q2", "query": "q2"},
        ]
        saved_queries = temp_pm.save_queries(project.id, queries)
        temp_pm.save_result(saved_queries[0].id, "https://example.com/1", "Title 1")
        temp_pm.save_result(saved_queries[1].id, "https://example.com/2", "Title 2")

        # Act
        results = temp_pm.get_all_results(project.id)

        # Assert
        assert len(results) == 2
