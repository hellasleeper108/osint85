"""Unit tests for scanner module."""

import pytest
from unittest.mock import MagicMock

from osint85.scanner import (
    SerpAPIClient,
    MockSearchClient,
    get_search_client,
    ResultProcessor,
    Scanner,
    SearchResult
)
from osint85.database import Target, Query


class TestSerpAPIClient:
    """Tests for SerpAPIClient."""

    def test_search_success(self, mocker):
        """Test that search returns results."""
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "organic_results": [
                {
                    "link": "https://example.com/1",
                    "title": "Result 1",
                    "snippet": "Snippet 1"
                },
                {
                    "link": "https://example.com/2",
                    "title": "Result 2",
                    "snippet": "Snippet 2"
                }
            ]
        }
        mock_get = mocker.patch('osint85.scanner.requests.get', return_value=mock_response)

        client = SerpAPIClient(api_key="test_key")

        # Act
        results = client.search("test query", num_results=10)

        # Assert
        assert len(results) == 2
        assert results[0].url == "https://example.com/1"
        assert results[0].title == "Result 1"
        assert results[0].snippet == "Snippet 1"
        assert results[0].source_engine == "google"
        mock_get.assert_called_once()

    def test_search_api_error(self, mocker):
        """Test that search raises error on API failure."""
        # Arrange
        mocker.patch('osint85.scanner.requests.get', side_effect=Exception("API Error"))

        client = SerpAPIClient(api_key="test_key")

        # Act & Assert
        with pytest.raises(RuntimeError, match="Search API error"):
            client.search("test query")

    def test_init_without_api_key(self, mocker):
        """Test that init raises error without API key."""
        mocker.patch('osint85.scanner.config.SEARCH_API_KEY', None)

        with pytest.raises(ValueError, match="SEARCH_API_KEY is required"):
            SerpAPIClient()

    def test_search_respects_num_results(self, mocker):
        """Test that search respects num_results parameter."""
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "organic_results": [
                {"link": f"https://example.com/{i}", "title": f"Result {i}", "snippet": f"Snippet {i}"}
                for i in range(50)
            ]
        }
        mocker.patch('osint85.scanner.requests.get', return_value=mock_response)

        client = SerpAPIClient(api_key="test_key")

        # Act
        results = client.search("test query", num_results=10)

        # Assert
        assert len(results) == 10


class TestMockSearchClient:
    """Tests for MockSearchClient."""

    def test_search_returns_mock_results(self):
        """Test that mock search returns results."""
        client = MockSearchClient()

        results = client.search("test query", num_results=10)

        assert len(results) > 0
        assert len(results) <= 5  # Mock returns max 5
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_extracts_domain_from_query(self):
        """Test that mock search extracts domain from query."""
        client = MockSearchClient()

        results = client.search("site:example.com test", num_results=10)

        assert all("example.com" in r.url for r in results)

    def test_search_handles_no_domain(self):
        """Test that mock search works without domain."""
        client = MockSearchClient()

        results = client.search("test query", num_results=10)

        assert len(results) > 0


class TestGetSearchClient:
    """Tests for get_search_client factory function."""

    def test_get_serpapi_client(self, mocker):
        """Test that get_search_client returns SerpAPIClient."""
        mocker.patch('osint85.scanner.config.SEARCH_API_KEY', 'test_key')

        client = get_search_client("serpapi")
        assert isinstance(client, SerpAPIClient)

    def test_get_mock_client(self):
        """Test that get_search_client returns MockSearchClient."""
        client = get_search_client(mock=True)
        assert isinstance(client, MockSearchClient)

    def test_invalid_provider(self):
        """Test that get_search_client raises error for invalid provider."""
        with pytest.raises(ValueError, match="Unsupported search provider"):
            get_search_client("invalid")


class TestResultProcessor:
    """Tests for ResultProcessor."""

    def test_tag_backup_urls(self):
        """Test that backup URLs are tagged correctly."""
        tags = ResultProcessor.tag_url("https://example.com/backup.zip")
        assert "backup" in tags

        tags = ResultProcessor.tag_url("https://example.com/old.sql")
        assert "backup" in tags

        tags = ResultProcessor.tag_url("https://example.com/data.tar.gz")
        assert "backup" in tags

    def test_tag_config_urls(self):
        """Test that config URLs are tagged correctly."""
        tags = ResultProcessor.tag_url("https://example.com/.env")
        assert "config" in tags

        tags = ResultProcessor.tag_url("https://example.com/config.yaml")
        assert "config" in tags

    def test_tag_dev_staging_urls(self):
        """Test that dev/staging URLs are tagged correctly."""
        tags = ResultProcessor.tag_url("https://staging.example.com/")
        assert "dev_staging" in tags

        tags = ResultProcessor.tag_url("https://dev.example.com/")
        assert "dev_staging" in tags

        tags = ResultProcessor.tag_url("https://test.example.com/")
        assert "dev_staging" in tags

    def test_tag_debug_urls(self):
        """Test that debug URLs are tagged correctly."""
        tags = ResultProcessor.tag_url("https://example.com/debug")
        assert "debug" in tags

        tags = ResultProcessor.tag_url("https://example.com/error.php")
        assert "debug" in tags

    def test_tag_login_urls(self):
        """Test that login URLs are tagged correctly."""
        tags = ResultProcessor.tag_url("https://example.com/login")
        assert "login" in tags

        tags = ResultProcessor.tag_url("https://example.com/admin")
        assert "login" in tags

        tags = ResultProcessor.tag_url("https://example.com/wp-admin")
        assert "login" in tags

    def test_tag_multiple_tags(self):
        """Test that URLs can have multiple tags."""
        tags = ResultProcessor.tag_url("https://dev.example.com/backup.zip")
        assert "backup" in tags
        assert "dev_staging" in tags

    def test_score_result_with_tags(self):
        """Test that scoring considers tags."""
        result = SearchResult(
            url="https://example.com/backup.zip",
            title="Backup File",
            snippet="Database backup"
        )
        tags = ["backup"]

        score = ResultProcessor.score_result(result, tags)
        assert score > 50  # Should have high score

    def test_score_result_with_keywords(self):
        """Test that scoring considers snippet keywords."""
        result = SearchResult(
            url="https://example.com/test",
            title="Test",
            snippet="Contains password and secret key information"
        )

        score = ResultProcessor.score_result(result, [])
        assert score > 50  # Should have high score due to keywords


class TestScanner:
    """Tests for Scanner class."""

    @pytest.fixture
    def mock_project_manager(self, mocker, temp_db, sample_target):
        """Create mock project manager."""
        from osint85.project import ProjectManager
        pm = ProjectManager(str(temp_db.db_path))
        return pm

    @pytest.fixture
    def sample_queries_objs(self, temp_db, sample_target):
        """Create sample query objects."""
        queries = [
            {
                "category": "test",
                "risk_level": "low",
                "description": "Test query 1",
                "query": "site:example.com test1"
            },
            {
                "category": "test",
                "risk_level": "medium",
                "description": "Test query 2",
                "query": "site:example.com test2"
            }
        ]
        return temp_db.save_queries(sample_target.id, queries)

    def test_run_scan(self, mock_project_manager, sample_target, sample_queries_objs):
        """Test that run executes queries and saves results."""
        # Arrange
        scanner = Scanner(mock_project_manager, mock=True)

        # Act
        scanner.run(sample_target, sample_queries_objs, max_results=5, delay=0)

        # Assert
        results = mock_project_manager.get_all_results(sample_target.id)
        assert len(results) > 0

    def test_run_single_query(self, mock_project_manager, sample_target, sample_queries_objs):
        """Test that run_single_query returns results without saving."""
        # Arrange
        scanner = Scanner(mock_project_manager, mock=True)

        # Act
        results = scanner.run_single_query(sample_queries_objs[0], max_results=5)

        # Assert
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
