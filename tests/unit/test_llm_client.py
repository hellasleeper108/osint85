"""Unit tests for LLM client module."""

import pytest
from unittest.mock import MagicMock, patch

from osint85.llm_client import (
    AnthropicClient,
    OpenAIClient,
    get_llm_client,
    parse_json_response
)


class TestAnthropicClient:
    """Tests for AnthropicClient."""

    def test_generate_success(self, mocker):
        """Test that generate returns response text."""
        # Arrange
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Generated response"
        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message
        
        mocker.patch('anthropic.Anthropic', return_value=mock_client)

        client = AnthropicClient(api_key="test_key")

        # Act
        result = client.generate(
            system_prompt="System prompt",
            user_prompt="User prompt"
        )

        # Assert
        assert result == "Generated response"
        mock_client.messages.create.assert_called_once()

    def test_generate_api_error(self, mocker):
        """Test that generate raises error on API failure."""
        # Arrange
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mocker.patch('anthropic.Anthropic', return_value=mock_client)

        client = AnthropicClient(api_key="test_key")

        # Act & Assert
        with pytest.raises(RuntimeError, match="Anthropic API error"):
            client.generate("System", "User")

    def test_init_without_api_key(self, mocker):
        """Test that init raises error without API key."""
        mocker.patch('anthropic.Anthropic')
        mocker.patch('osint85.llm_client.config.ANTHROPIC_API_KEY', None)

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
            AnthropicClient()


class TestOpenAIClient:
    """Tests for OpenAIClient."""

    def test_generate_success(self, mocker):
        """Test that generate returns response text."""
        # Arrange
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Generated response"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        
        mocker.patch('openai.OpenAI', return_value=mock_client)

        client = OpenAIClient(api_key="test_key")

        # Act
        result = client.generate(
            system_prompt="System prompt",
            user_prompt="User prompt"
        )

        # Assert
        assert result == "Generated response"
        mock_client.chat.completions.create.assert_called_once()

    def test_generate_api_error(self, mocker):
        """Test that generate raises error on API failure."""
        # Arrange
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mocker.patch('openai.OpenAI', return_value=mock_client)

        client = OpenAIClient(api_key="test_key")

        # Act & Assert
        with pytest.raises(RuntimeError, match="OpenAI API error"):
            client.generate("System", "User")

    def test_init_without_api_key(self, mocker):
        """Test that init raises error without API key."""
        mocker.patch('openai.OpenAI')
        mocker.patch('osint85.llm_client.config.OPENAI_API_KEY', None)

        with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
            OpenAIClient()


class TestGetLLMClient:
    """Tests for get_llm_client factory function."""

    def test_get_anthropic_client(self, mocker):
        """Test that get_llm_client returns AnthropicClient."""
        mocker.patch('anthropic.Anthropic')
        mocker.patch('osint85.llm_client.config.ANTHROPIC_API_KEY', 'test_key')

        client = get_llm_client("anthropic")
        assert isinstance(client, AnthropicClient)

    def test_get_openai_client(self, mocker):
        """Test that get_llm_client returns OpenAIClient."""
        mocker.patch('openai.OpenAI')
        mocker.patch('osint85.llm_client.config.OPENAI_API_KEY', 'test_key')

        client = get_llm_client("openai")
        assert isinstance(client, OpenAIClient)

    def test_invalid_provider(self):
        """Test that get_llm_client raises error for invalid provider."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            get_llm_client("invalid")


class TestParseJSONResponse:
    """Tests for parse_json_response function."""

    def test_parse_plain_json(self):
        """Test parsing plain JSON string."""
        json_str = '{"key": "value"}'
        result = parse_json_response(json_str)
        assert result == {"key": "value"}

    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code block."""
        json_str = '```json\n{"key": "value"}\n```'
        result = parse_json_response(json_str)
        assert result == {"key": "value"}

    def test_parse_json_with_generic_code_block(self):
        """Test parsing JSON in generic code block."""
        json_str = '```\n{"key": "value"}\n```'
        result = parse_json_response(json_str)
        assert result == {"key": "value"}

    def test_parse_invalid_json(self):
        """Test that invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            parse_json_response("not json")

    def test_parse_complex_json(self):
        """Test parsing complex nested JSON."""
        json_str = '''
        ```json
        {
          "queries": [
            {"category": "test", "query": "example"},
            {"category": "test2", "query": "example2"}
          ]
        }
        ```
        '''
        result = parse_json_response(json_str)
        assert "queries" in result
        assert len(result["queries"]) == 2
