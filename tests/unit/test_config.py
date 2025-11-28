"""Unit tests for config module."""

import pytest
import os
from pathlib import Path

from osint85.config import Config


class TestConfig:
    """Tests for Config class."""

    def test_default_values(self, mocker):
        """Test that default values are set correctly."""
        # Arrange - mock environment to be empty
        mocker.patch.dict(os.environ, {}, clear=True)

        # Act - reload config
        from importlib import reload
        import osint85.config as config_module
        reload(config_module)

        # Assert
        assert config_module.Config.LOG_LEVEL == "INFO"
        assert config_module.Config.MAX_RETRIES == 3
        assert config_module.Config.REQUEST_TIMEOUT == 30
        assert config_module.Config.DATABASE_PATH == ".osint85/project.db"

    def test_environment_overrides(self, mocker):
        """Test that environment variables override defaults."""
        # Arrange
        mocker.patch.dict(os.environ, {
            'LOG_LEVEL': 'DEBUG',
            'MAX_RETRIES': '5',
            'REQUEST_TIMEOUT': '60',
            'DATABASE_PATH': 'custom.db'
        })

        # Act - reload config
        from importlib import reload
        import osint85.config as config_module
        reload(config_module)

        # Assert
        assert config_module.Config.LOG_LEVEL == "DEBUG"
        assert config_module.Config.MAX_RETRIES == 5
        assert config_module.Config.REQUEST_TIMEOUT == 60
        assert config_module.Config.DATABASE_PATH == "custom.db"

    def test_validate_with_anthropic_key(self, mocker):
        """Test that validate passes with Anthropic API key."""
        # Arrange
        mocker.patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test_key',
            'SEARCH_API_KEY': 'test_search_key',
            'DEFAULT_LLM_PROVIDER': 'anthropic'
        })

        # Act - reload config
        from importlib import reload
        import osint85.config as config_module
        reload(config_module)

        # Assert
        assert config_module.Config.validate() is True

    def test_validate_with_openai_key(self, mocker):
        """Test that validate passes with OpenAI API key."""
        # Arrange
        mocker.patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test_key',
            'SEARCH_API_KEY': 'test_search_key',
            'DEFAULT_LLM_PROVIDER': 'openai'
        })

        # Act - reload config
        from importlib import reload
        import osint85.config as config_module
        reload(config_module)

        # Assert
        assert config_module.Config.validate() is True

    def test_validate_fails_without_llm_key(self, mocker, capsys):
        """Test that validate fails without LLM API key."""
        # Arrange
        mocker.patch.dict(os.environ, {
            'SEARCH_API_KEY': 'test_search_key',
            'DEFAULT_LLM_PROVIDER': 'anthropic'
        }, clear=True)

        # Act - reload config
        from importlib import reload
        import osint85.config as config_module
        reload(config_module)

        result = config_module.Config.validate()

        # Assert
        assert result is False
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY is required" in captured.out

    def test_validate_fails_without_search_key(self, mocker, capsys):
        """Test that validate fails without search API key."""
        # Arrange
        mocker.patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test_key',
            'DEFAULT_LLM_PROVIDER': 'anthropic'
        }, clear=True)

        # Act - reload config
        from importlib import reload
        import osint85.config as config_module
        reload(config_module)

        result = config_module.Config.validate()

        # Assert
        assert result is False
        captured = capsys.readouterr()
        assert "SEARCH_API_KEY is required" in captured.out

    def test_ensure_directories(self, mocker):
        """Test that ensure_directories creates required directories."""
        # Arrange
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())

        reports_dir = temp_dir / "reports"
        osint_dir = temp_dir / ".osint85"

        mocker.patch('osint85.config.Config.REPORTS_DIR', reports_dir)
        mocker.patch('osint85.config.Config.OSINT_DIR', osint_dir)

        # Act
        # Act
        from osint85.config import Config
        Config.ensure_directories()

        # Assert
        assert reports_dir.exists()
        assert osint_dir.exists()

        # Cleanup
        reports_dir.rmdir()
        osint_dir.rmdir()
        temp_dir.rmdir()

    def test_rate_limits(self, mocker):
        """Test that rate limits can be configured."""
        # Arrange
        mocker.patch.dict(os.environ, {
            'SEARCH_RATE_LIMIT': '20',
            'LLM_RATE_LIMIT': '100'
        })

        # Act - reload config
        from importlib import reload
        import osint85.config as config_module
        reload(config_module)

        # Assert
        assert config_module.Config.SEARCH_RATE_LIMIT == 20
        assert config_module.Config.LLM_RATE_LIMIT == 100

    def test_search_provider_config(self, mocker):
        """Test that search provider can be configured."""
        # Arrange
        mocker.patch.dict(os.environ, {
            'SEARCH_API_PROVIDER': 'custom_provider'
        })

        # Act - reload config
        from importlib import reload
        import osint85.config as config_module
        reload(config_module)

        # Assert
        assert config_module.Config.SEARCH_API_PROVIDER == "custom_provider"
