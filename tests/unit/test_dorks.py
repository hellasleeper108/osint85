"""Unit tests for dork generator module."""

import pytest
from unittest.mock import MagicMock

from osint85.dorks import DorkGenerator
from osint85.database import Target


class TestDorkGenerator:
    """Tests for DorkGenerator class."""

    @pytest.fixture
    def mock_llm_client(self, mocker):
        """Mock LLM client."""
        mock_client = MagicMock()
        mocker.patch('osint85.dorks.get_llm_client', return_value=mock_client)
        return mock_client

    @pytest.fixture
    def sample_target(self):
        """Create a sample target."""
        return Target(
            id=1,
            name="Test Target",
            primary_domain="example.com",
            notes="Test notes",
            scope="Bug bounty program",
            created_at="2024-01-01"
        )

    def test_generate_success(self, mock_llm_client, sample_target):
        """Test that generate returns parsed queries."""
        # Arrange
        mock_response = """{
  "queries": [
    {
      "category": "exposed_backups",
      "risk_level": "high",
      "description": "Find backup files",
      "query": "site:example.com backup"
    },
    {
      "category": "config_files",
      "risk_level": "medium",
      "description": "Find config files",
      "query": "site:example.com .config"
    }
  ]
}"""
        mock_llm_client.generate.return_value = mock_response

        generator = DorkGenerator()

        # Act
        result = generator.generate(sample_target, "Find exposed files")

        # Assert
        assert len(result) == 2
        assert result[0]["category"] == "exposed_backups"
        assert result[0]["risk_level"] == "high"
        assert result[1]["category"] == "config_files"
        mock_llm_client.generate.assert_called_once()

    def test_generate_with_markdown_wrapped_json(self, mock_llm_client, sample_target):
        """Test that generate handles markdown-wrapped JSON."""
        # Arrange
        mock_response = """```json
{
  "queries": [
    {
      "category": "test",
      "risk_level": "low",
      "description": "Test query",
      "query": "test"
    }
  ]
}
```"""
        mock_llm_client.generate.return_value = mock_response

        generator = DorkGenerator()

        # Act
        result = generator.generate(sample_target, "Test goal")

        # Assert
        assert len(result) == 1
        assert result[0]["category"] == "test"

    def test_generate_llm_error(self, mock_llm_client, sample_target):
        """Test that generate raises error on LLM failure."""
        # Arrange
        mock_llm_client.generate.side_effect = Exception("LLM Error")

        generator = DorkGenerator()

        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to generate dorks"):
            generator.generate(sample_target, "Test goal")

    def test_generate_invalid_json(self, mock_llm_client, sample_target):
        """Test that generate raises error on invalid JSON."""
        # Arrange
        mock_llm_client.generate.return_value = "not json"

        generator = DorkGenerator()

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to parse LLM response"):
            generator.generate(sample_target, "Test goal")

    def test_generate_no_queries(self, mock_llm_client, sample_target):
        """Test that generate raises error when no queries returned."""
        # Arrange
        mock_llm_client.generate.return_value = '{"queries": []}'

        generator = DorkGenerator()

        # Act & Assert
        with pytest.raises(ValueError, match="No queries generated"):
            generator.generate(sample_target, "Test goal")

    def test_generate_invalid_query_structure(self, mock_llm_client, sample_target):
        """Test that generate raises error on invalid query structure."""
        # Arrange
        mock_response = """{
  "queries": [
    {
      "category": "test",
      "query": "missing fields"
    }
  ]
}"""
        mock_llm_client.generate.return_value = mock_response

        generator = DorkGenerator()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid query structure"):
            generator.generate(sample_target, "Test goal")

    def test_generate_for_categories(self, mock_llm_client, sample_target):
        """Test generate_for_categories method."""
        # Arrange
        mock_response = """{
  "queries": [
    {
      "category": "exposed_backups",
      "risk_level": "high",
      "description": "Test",
      "query": "test"
    }
  ]
}"""
        mock_llm_client.generate.return_value = mock_response

        generator = DorkGenerator()

        # Act
        result = generator.generate_for_categories(
            sample_target,
            ["exposed_backups", "config_files"]
        )

        # Assert
        assert len(result) == 1
        mock_llm_client.generate.assert_called_once()
        # Check that goal contains the categories
        call_args = mock_llm_client.generate.call_args
        assert "exposed_backups" in call_args[1]["user_prompt"]
        assert "config_files" in call_args[1]["user_prompt"]

    def test_generate_comprehensive(self, mock_llm_client, sample_target):
        """Test generate_comprehensive method."""
        # Arrange
        mock_response = """{
  "queries": [
    {
      "category": "exposed_backups",
      "risk_level": "high",
      "description": "Test",
      "query": "test"
    }
  ]
}"""
        mock_llm_client.generate.return_value = mock_response

        generator = DorkGenerator()

        # Act
        result = generator.generate_comprehensive(sample_target)

        # Assert
        assert len(result) == 1
        mock_llm_client.generate.assert_called_once()
        # Check that comprehensive goal is used
        call_args = mock_llm_client.generate.call_args
        assert "comprehensive" in call_args[1]["user_prompt"].lower()

    def test_system_prompt_structure(self, mock_llm_client, sample_target):
        """Test that system prompt is properly formatted."""
        # Arrange
        mock_response = """{
  "queries": [
    {
      "category": "test",
      "risk_level": "low",
      "description": "Test",
      "query": "test"
    }
  ]
}"""
        mock_llm_client.generate.return_value = mock_response

        generator = DorkGenerator()

        # Act
        generator.generate(sample_target, "Test goal")

        # Assert
        call_args = mock_llm_client.generate.call_args
        system_prompt = call_args[1]["system_prompt"]
        assert "search-operator queries" in system_prompt
        assert "pure JSON" in system_prompt
        assert "category" in system_prompt
        assert "risk_level" in system_prompt
