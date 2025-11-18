"""Unit tests for reporting module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from osint85.reporting import Reporter
from osint85.project import ProjectManager
from osint85.database import Target


class TestReporter:
    """Tests for Reporter class."""

    @pytest.fixture
    def temp_pm(self):
        """Create temporary project manager."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        pm = ProjectManager(db_path)
        yield pm
        pm.close()

        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def project_with_results(self, temp_pm):
        """Create a project with queries and results."""
        # Create project
        project = temp_pm.create_project("Test", "example.com")

        # Create queries
        queries = [
            {
                "category": "exposed_backups",
                "risk_level": "high",
                "description": "Find backups",
                "query": "test"
            },
            {
                "category": "config_files",
                "risk_level": "medium",
                "description": "Find configs",
                "query": "test2"
            }
        ]
        saved_queries = temp_pm.save_queries(project.id, queries)

        # Create results
        temp_pm.save_result(
            saved_queries[0].id,
            "https://example.com/backup.zip",
            "Backup File",
            "Database backup",
            "google",
            "backup"
        )
        temp_pm.save_result(
            saved_queries[1].id,
            "https://example.com/.env",
            "Config File",
            "Environment config",
            "google",
            "config"
        )

        return project

    @pytest.fixture
    def mock_llm_client(self, mocker):
        """Mock LLM client."""
        mock_client = MagicMock()
        mocker.patch('osint85.reporting.get_llm_client', return_value=mock_client)
        return mock_client

    def test_generate_with_llm(self, temp_pm, project_with_results, mock_llm_client):
        """Test that generate creates a report using LLM."""
        # Arrange
        mock_llm_client.generate.return_value = """# OSINT Report

## Findings

Test report content"""

        reporter = Reporter(temp_pm)

        # Act
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            report_path = f.name

        try:
            report = reporter.generate(project_with_results, out_path=report_path)

            # Assert
            assert "# OSINT Report" in report
            assert Path(report_path).exists()
            content = Path(report_path).read_text()
            assert "# OSINT Report" in content
            assert project_with_results.name in content
            mock_llm_client.generate.assert_called_once()
        finally:
            Path(report_path).unlink(missing_ok=True)

    def test_generate_without_results(self, temp_pm, mock_llm_client):
        """Test that generate handles projects with no results."""
        # Arrange
        project = temp_pm.create_project("Empty Project", "example.com")
        reporter = Reporter(temp_pm)

        # Act
        report = reporter.generate(project)

        # Assert
        assert "No results found" in report
        mock_llm_client.generate.assert_not_called()

    def test_generate_fallback_on_llm_error(self, temp_pm, project_with_results, mock_llm_client):
        """Test that generate falls back to basic report on LLM error."""
        # Arrange
        mock_llm_client.generate.side_effect = Exception("LLM Error")
        reporter = Reporter(temp_pm)

        # Act
        report = reporter.generate(project_with_results)

        # Assert
        assert "# OSINT Report" in report
        assert project_with_results.name in report
        assert "example.com" in report

    def test_generate_summary(self, temp_pm, project_with_results):
        """Test that generate_summary creates a summary."""
        # Arrange
        reporter = Reporter(temp_pm)

        # Act
        summary = reporter.generate_summary(project_with_results)

        # Assert
        assert project_with_results.name in summary
        assert "example.com" in summary
        assert "Queries:" in summary
        assert "Results:" in summary

    def test_group_by_category(self, temp_pm, project_with_results):
        """Test that _group_by_category groups results correctly."""
        # Arrange
        reporter = Reporter(temp_pm)
        results = temp_pm.get_all_results(project_with_results.id)
        queries = temp_pm.list_queries(project_with_results.id)
        query_map = {q.id: q for q in queries}

        # Act
        grouped = reporter._group_by_category(results, query_map)

        # Assert
        assert "exposed_backups" in grouped
        assert "config_files" in grouped
        assert len(grouped["exposed_backups"]) == 1
        assert len(grouped["config_files"]) == 1

    def test_prepare_llm_input(self, temp_pm, project_with_results):
        """Test that _prepare_llm_input formats data correctly."""
        # Arrange
        reporter = Reporter(temp_pm)
        results = temp_pm.get_all_results(project_with_results.id)
        queries = temp_pm.list_queries(project_with_results.id)
        query_map = {q.id: q for q in queries}
        grouped = reporter._group_by_category(results, query_map)

        # Act
        llm_input = reporter._prepare_llm_input(project_with_results, grouped)

        # Assert
        assert project_with_results.name in llm_input
        assert "example.com" in llm_input
        assert "exposed_backups" in llm_input
        assert "config_files" in llm_input

    def test_generate_basic_report(self, temp_pm, project_with_results):
        """Test that _generate_basic_report creates a fallback report."""
        # Arrange
        reporter = Reporter(temp_pm)
        results = temp_pm.get_all_results(project_with_results.id)
        queries = temp_pm.list_queries(project_with_results.id)
        query_map = {q.id: q for q in queries}
        grouped = reporter._group_by_category(results, query_map)

        # Act
        report = reporter._generate_basic_report(project_with_results, grouped)

        # Assert
        assert "# OSINT Report" in report
        assert project_with_results.name in report
        assert "Exposed Backups" in report
        assert "Config Files" in report
        assert "example.com/backup.zip" in report
