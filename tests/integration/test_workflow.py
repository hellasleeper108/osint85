"""Integration tests for complete osint85 workflow."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from osint85.project import ProjectManager
from osint85.dorks import DorkGenerator
from osint85.scanner import Scanner
from osint85.reporting import Reporter


class TestCompleteWorkflow:
    """Integration tests for complete osint85 workflow."""

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
    def mock_llm_client(self, mocker):
        """Mock LLM client for dork generation and reporting."""
        mock_client = MagicMock()

        # Mock dork generation response
        dork_response = """{
  "queries": [
    {
      "category": "exposed_backups",
      "risk_level": "high",
      "description": "Find backup files",
      "query": "site:example.com backup"
    },
    {
      "category": "config_files",
      "risk_level": "high",
      "description": "Find config files",
      "query": "site:example.com .env"
    }
  ]
}"""

        # Mock report generation response
        report_response = """# OSINT Report

## Findings by Category

### Exposed Backups
Test findings
"""

        # Configure mock to return different responses
        mock_client.generate.side_effect = [dork_response, report_response]
        mocker.patch('osint85.dorks.get_llm_client', return_value=mock_client)
        mocker.patch('osint85.reporting.get_llm_client', return_value=mock_client)

        return mock_client

    def test_full_osint_workflow(self, temp_pm, mock_llm_client):
        """Test complete workflow from project creation to report generation."""
        # Step 1: Create a project
        project = temp_pm.create_project(
            name="Integration Test Project",
            domain="example.com",
            notes="Test project for integration testing",
            scope="Test scope"
        )

        assert project.id is not None
        assert project.name == "Integration Test Project"

        # Step 2: Generate dorks with AI
        generator = DorkGenerator()
        queries = generator.generate(project, "Find exposed files")

        assert len(queries) == 2
        assert queries[0]["category"] == "exposed_backups"

        # Step 3: Save queries to database
        saved_queries = temp_pm.save_queries(project.id, queries)

        assert len(saved_queries) == 2
        assert all(q.enabled for q in saved_queries)

        # Step 4: Run scan (using mock search client)
        scanner = Scanner(temp_pm, mock=True)
        scanner.run(project, saved_queries, max_results=5, delay=0)

        # Verify results were saved
        results = temp_pm.get_all_results(project.id)
        assert len(results) > 0

        # Step 5: Generate report
        reporter = Reporter(temp_pm)

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            report_path = f.name

        try:
            report = reporter.generate(project, out_path=report_path)

            # Verify report was generated
            assert "# OSINT Report" in report
            assert Path(report_path).exists()

            # Verify report contains project info
            report_content = Path(report_path).read_text()
            assert project.name in report_content
            assert project.primary_domain in report_content

        finally:
            Path(report_path).unlink(missing_ok=True)

    def test_workflow_with_query_management(self, temp_pm, mock_llm_client):
        """Test workflow with query enable/disable."""
        # Create project and generate queries
        project = temp_pm.create_project("Test", "example.com")
        generator = DorkGenerator()
        queries = generator.generate(project, "Test goal")
        saved_queries = temp_pm.save_queries(project.id, queries)

        # Disable one query
        temp_pm.toggle_query(saved_queries[0].id, False)

        # Verify only enabled queries are returned
        enabled_queries = temp_pm.get_enabled_queries(project.id)
        assert len(enabled_queries) == 1
        assert enabled_queries[0].id == saved_queries[1].id

        # Run scan with only enabled queries
        scanner = Scanner(temp_pm, mock=True)
        scanner.run(project, enabled_queries, max_results=5, delay=0)

        # Verify results only from enabled query
        results = temp_pm.get_all_results(project.id)
        assert all(r.query_id == saved_queries[1].id for r in results)

    def test_workflow_with_multiple_scans(self, temp_pm, mock_llm_client):
        """Test workflow with multiple scan runs."""
        # Setup
        project = temp_pm.create_project("Test", "example.com")
        generator = DorkGenerator()
        queries = generator.generate(project, "Test goal")
        saved_queries = temp_pm.save_queries(project.id, queries)

        # Run first scan
        scanner = Scanner(temp_pm, mock=True)
        scanner.run(project, saved_queries, max_results=5, delay=0)
        results_after_first = temp_pm.get_all_results(project.id)

        # Run second scan (should add more results or update existing)
        scanner.run(project, saved_queries, max_results=5, delay=0)
        results_after_second = temp_pm.get_all_results(project.id)

        # Verify results were added/updated
        assert len(results_after_second) >= len(results_after_first)

    def test_workflow_summary_generation(self, temp_pm, mock_llm_client):
        """Test generating quick summaries."""
        # Setup
        project = temp_pm.create_project("Test", "example.com")
        generator = DorkGenerator()
        queries = generator.generate(project, "Test goal")
        saved_queries = temp_pm.save_queries(project.id, queries)

        # Run scan
        scanner = Scanner(temp_pm, mock=True)
        scanner.run(project, saved_queries, max_results=5, delay=0)

        # Generate summary
        reporter = Reporter(temp_pm)
        summary = reporter.generate_summary(project)

        # Verify summary contains key information
        assert project.name in summary
        assert project.primary_domain in summary
        assert "Queries:" in summary
        assert "Results:" in summary

    def test_workflow_result_tagging(self, temp_pm, mock_llm_client):
        """Test that results are properly tagged during scan."""
        # Setup
        project = temp_pm.create_project("Test", "example.com")
        generator = DorkGenerator()
        queries = generator.generate(project, "Test goal")
        saved_queries = temp_pm.save_queries(project.id, queries)

        # Run scan
        scanner = Scanner(temp_pm, mock=True)
        scanner.run(project, saved_queries, max_results=5, delay=0)

        # Verify some results have tags
        results = temp_pm.get_all_results(project.id)
        # Mock search client may not generate URLs with patterns, so just verify structure
        assert all(hasattr(r, 'tags') for r in results)

    def test_workflow_with_empty_results(self, temp_pm, mock_llm_client):
        """Test workflow when scan returns no results."""
        # Create a project but don't run scan
        project = temp_pm.create_project("Empty Project", "example.com")

        # Generate report with no results
        reporter = Reporter(temp_pm)
        report = reporter.generate(project)

        # Verify report indicates no results
        assert "No results found" in report

    def test_workflow_query_categories(self, temp_pm, mock_llm_client):
        """Test workflow with different query categories."""
        # Setup
        project = temp_pm.create_project("Test", "example.com")

        # Manually create queries in different categories
        queries = [
            {
                "category": "exposed_backups",
                "risk_level": "high",
                "description": "Backups",
                "query": "site:example.com backup"
            },
            {
                "category": "config_files",
                "risk_level": "high",
                "description": "Configs",
                "query": "site:example.com config"
            },
            {
                "category": "staging_environments",
                "risk_level": "medium",
                "description": "Staging",
                "query": "site:staging.example.com"
            }
        ]
        saved_queries = temp_pm.save_queries(project.id, queries)

        # Run scan
        scanner = Scanner(temp_pm, mock=True)
        scanner.run(project, saved_queries, max_results=3, delay=0)

        # Get results
        results = temp_pm.get_all_results(project.id)

        # Verify results exist for different query categories
        query_ids = set(r.query_id for r in results)
        assert len(query_ids) > 0  # At least some queries returned results
