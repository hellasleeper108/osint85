"""Test fixtures for osint85 tests."""

import pytest
import tempfile
from pathlib import Path
from osint85.database import Database, Target


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = Database(db_path)
    yield db
    db.close()

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_target(temp_db):
    """Create a sample target for testing."""
    return temp_db.create_target(
        name="Test Target",
        primary_domain="example.com",
        notes="Test notes",
        scope="Test scope"
    )


@pytest.fixture
def sample_queries():
    """Sample query data for testing."""
    return [
        {
            "category": "exposed_backups",
            "risk_level": "high",
            "description": "Find backup files",
            "query": 'site:example.com ext:zip OR ext:tar "backup"'
        },
        {
            "category": "config_files",
            "risk_level": "high",
            "description": "Find .env files",
            "query": 'site:example.com ".env"'
        },
        {
            "category": "staging_environments",
            "risk_level": "medium",
            "description": "Find staging subdomains",
            "query": 'site:staging.example.com OR site:dev.example.com'
        }
    ]


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for dork generation."""
    return """{
  "queries": [
    {
      "category": "exposed_backups",
      "risk_level": "high",
      "description": "Find backup archives",
      "query": "site:example.com ext:zip OR ext:tar backup"
    },
    {
      "category": "exposed_backups",
      "risk_level": "high",
      "description": "Find SQL dumps",
      "query": "site:example.com ext:sql OR ext:dump"
    },
    {
      "category": "config_files",
      "risk_level": "high",
      "description": "Find environment files",
      "query": "site:example.com .env OR config.json"
    }
  ]
}"""


@pytest.fixture
def mock_llm_report_response():
    """Mock LLM response for report generation."""
    return """# OSINT Reconnaissance Report

## Executive Summary

During authorized reconnaissance, 3 findings were identified across multiple categories.

## Findings by Category

### Exposed Backups
**Risk Level:** High

**URLs Found:**
- https://example.com/backup.zip - Backup archive file

**Security Implications:**
These backup files may contain sensitive data.

**Recommendations:**
- Remove public access to backup files
- Implement authentication

## Overall Recommendations

1. Secure all exposed backup files
2. Implement access controls
"""


@pytest.fixture
def mock_search_results():
    """Mock search API results."""
    return {
        "organic_results": [
            {
                "link": "https://example.com/backup.zip",
                "title": "Backup Archive",
                "snippet": "Database backup from 2024"
            },
            {
                "link": "https://example.com/.env",
                "title": "Environment Configuration",
                "snippet": "Configuration file with settings"
            },
            {
                "link": "https://staging.example.com/",
                "title": "Staging Environment",
                "snippet": "Development staging server"
            }
        ]
    }


@pytest.fixture
def mock_anthropic_client(mocker):
    """Mock Anthropic client."""
    mock_client = mocker.MagicMock()
    mock_message = mocker.MagicMock()
    mock_content = mocker.MagicMock()
    mock_content.text = '{"queries": []}'
    mock_message.content = [mock_content]
    mock_client.messages.create.return_value = mock_message
    return mock_client


@pytest.fixture
def mock_openai_client(mocker):
    """Mock OpenAI client."""
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_choice = mocker.MagicMock()
    mock_message = mocker.MagicMock()
    mock_message.content = '{"queries": []}'
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client
