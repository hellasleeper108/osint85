"""
Pytest configuration and fixtures for OSINT-85 tests.

Provides common fixtures for database, mocked LLM/API responses, and test data.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from osint85.database import Database, Target, Query, Result
from osint85.project import ProjectManager
from osint85.cache import CacheManager


# Test Data Constants

MOCK_TARGET = {
    "name": "Test Target",
    "primary_domain": "example.com",
    "notes": "Test target for unit tests",
    "scope": "*.example.com"
}

MOCK_QUERIES = [
    {
        "category": "exposed_files",
        "risk_level": "high",
        "description": "Find exposed configuration files",
        "query": 'site:example.com filetype:env'
    },
    {
        "category": "exposed_files",
        "risk_level": "medium",
        "description": "Find backup files",
        "query": 'site:example.com filetype:bak'
    },
    {
        "category": "subdomains",
        "risk_level": "low",
        "description": "Discover subdomains",
        "query": 'site:*.example.com -www'
    }
]

MOCK_RESULTS = [
    {
        "url": "https://example.com/config.env",
        "title": "Configuration File",
        "snippet": "Database credentials exposed in config file",
        "source_engine": "mock",
        "tags": "credentials,config,high-risk"
    },
    {
        "url": "https://example.com/backup.bak",
        "title": "Backup File",
        "snippet": "Old backup file with sensitive data",
        "source_engine": "mock",
        "tags": "backup,sensitive"
    },
    {
        "url": "https://api.example.com",
        "title": "API Subdomain",
        "snippet": "API endpoint discovered",
        "source_engine": "mock",
        "tags": "subdomain,api"
    }
]

MOCK_LLM_QUERY_RESPONSE = """
{
  "queries": [
    {
      "category": "exposed_files",
      "risk_level": "high",
      "description": "Environment configuration files",
      "query": "site:example.com filetype:env"
    },
    {
      "category": "exposed_files",
      "risk_level": "high",
      "description": "Database backup files",
      "query": "site:example.com ext:sql"
    }
  ]
}
"""

MOCK_LLM_SUMMARY_RESPONSE = """
## Security Analysis Summary

### Critical Findings
- Exposed configuration files containing database credentials
- Publicly accessible backup files

### Recommendations
1. Remove exposed configuration files immediately
2. Implement proper access controls
3. Review backup retention policies
"""


# Pytest Fixtures

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_db(temp_dir):
    """Create a test database instance."""
    db_path = temp_dir / "test.db"
    db = Database(str(db_path))
    yield db
    db.close()


@pytest.fixture
def test_db_with_data(test_db):
    """Create a test database with sample data."""
    # Create target
    target = test_db.create_target(
        name=MOCK_TARGET["name"],
        primary_domain=MOCK_TARGET["primary_domain"],
        notes=MOCK_TARGET["notes"],
        scope=MOCK_TARGET["scope"]
    )

    # Create queries
    queries = test_db.save_queries(target.id, MOCK_QUERIES)

    # Create results
    for query in queries:
        for result_data in MOCK_RESULTS:
            test_db.save_result(
                query_id=query.id,
                url=result_data["url"],
                title=result_data["title"],
                snippet=result_data["snippet"],
                source_engine=result_data["source_engine"],
                tags=result_data["tags"]
            )

    yield test_db, target, queries


@pytest.fixture
def test_project_manager(temp_dir, monkeypatch):
    """Create a test project manager with isolated database."""
    # Set test database path
    test_db_path = temp_dir / "project.db"
    monkeypatch.setattr("osint85.project.DB_PATH", str(test_db_path))

    pm = ProjectManager()
    yield pm
    pm.db.close()


@pytest.fixture
def test_cache_dir(temp_dir):
    """Create a temporary cache directory."""
    cache_path = temp_dir / "cache"
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


@pytest.fixture
def test_cache_manager(test_cache_dir):
    """Create a test cache manager."""
    return CacheManager(test_cache_dir)


@pytest.fixture
def mock_llm_client(mocker):
    """Mock LLM client for testing."""
    mock_client = mocker.MagicMock()

    # Mock generate method
    mock_client.generate.return_value = MOCK_LLM_QUERY_RESPONSE

    # Mock async generate
    async def mock_generate_async(*args, **kwargs):
        return MOCK_LLM_QUERY_RESPONSE

    mock_client.generate_async = mock_generate_async

    return mock_client


@pytest.fixture
def mock_search_client(mocker):
    """Mock search API client for testing."""
    mock_client = mocker.MagicMock()

    # Mock search method
    mock_client.search.return_value = [
        {
            "url": result["url"],
            "title": result["title"],
            "snippet": result["snippet"]
        }
        for result in MOCK_RESULTS
    ]

    # Mock async search
    async def mock_search_async(*args, **kwargs):
        return [
            {
                "url": result["url"],
                "title": result["title"],
                "snippet": result["snippet"]
            }
            for result in MOCK_RESULTS
        ]

    mock_client.search_async = mock_search_async

    return mock_client


@pytest.fixture
def sample_target():
    """Return a sample Target object."""
    return Target(
        id=1,
        name=MOCK_TARGET["name"],
        primary_domain=MOCK_TARGET["primary_domain"],
        notes=MOCK_TARGET["notes"],
        scope=MOCK_TARGET["scope"],
        created_at=datetime.now().isoformat()
    )


@pytest.fixture
def sample_query():
    """Return a sample Query object."""
    return Query(
        id=1,
        target_id=1,
        category=MOCK_QUERIES[0]["category"],
        risk_level=MOCK_QUERIES[0]["risk_level"],
        description=MOCK_QUERIES[0]["description"],
        query=MOCK_QUERIES[0]["query"],
        enabled=True,
        created_at=datetime.now().isoformat()
    )


@pytest.fixture
def sample_result():
    """Return a sample Result object."""
    return Result(
        id=1,
        query_id=1,
        url=MOCK_RESULTS[0]["url"],
        title=MOCK_RESULTS[0]["title"],
        snippet=MOCK_RESULTS[0]["snippet"],
        source_engine=MOCK_RESULTS[0]["source_engine"],
        tags=MOCK_RESULTS[0]["tags"],
        first_seen_at=datetime.now().isoformat(),
        last_seen_at=datetime.now().isoformat()
    )


@pytest.fixture
def sample_results_list():
    """Return a list of sample Result objects."""
    return [
        Result(
            id=i + 1,
            query_id=1,
            url=result["url"],
            title=result["title"],
            snippet=result["snippet"],
            source_engine=result["source_engine"],
            tags=result["tags"],
            first_seen_at=datetime.now().isoformat(),
            last_seen_at=datetime.now().isoformat()
        )
        for i, result in enumerate(MOCK_RESULTS)
    ]


# Snapshot Testing Helpers

@pytest.fixture
def snapshot_dir(temp_dir):
    """Create directory for snapshot files."""
    snap_path = temp_dir / "snapshots"
    snap_path.mkdir(parents=True, exist_ok=True)
    return snap_path


def normalize_llm_output(output: str) -> str:
    """Normalize LLM output for snapshot comparison."""
    # Remove timestamps, dynamic IDs, etc.
    import re

    # Remove ISO timestamps
    output = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', 'TIMESTAMP', output)

    # Remove UUIDs
    output = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'UUID', output)

    # Normalize whitespace
    output = re.sub(r'\s+', ' ', output).strip()

    return output


@pytest.fixture
def llm_snapshot_matcher(snapshot_dir):
    """Create a snapshot matcher for LLM outputs."""
    def match(test_name: str, output: str) -> bool:
        """Match output against saved snapshot."""
        snapshot_file = snapshot_dir / f"{test_name}.txt"
        normalized = normalize_llm_output(output)

        if snapshot_file.exists():
            # Compare with existing snapshot
            expected = snapshot_file.read_text()
            return normalized == normalize_llm_output(expected)
        else:
            # Save new snapshot
            snapshot_file.write_text(output)
            return True

    return match


# Mock Data Generators

def generate_mock_results(count: int, base_url: str = "https://example.com") -> List[Dict[str, Any]]:
    """Generate mock search results for testing."""
    return [
        {
            "url": f"{base_url}/page{i}.html",
            "title": f"Test Page {i}",
            "snippet": f"This is test result {i} with some content",
            "source_engine": "mock",
            "tags": f"test,page{i}"
        }
        for i in range(count)
    ]


def generate_mock_queries(count: int, category: str = "test") -> List[Dict[str, str]]:
    """Generate mock queries for testing."""
    return [
        {
            "category": category,
            "risk_level": "medium",
            "description": f"Test query {i}",
            "query": f"site:example.com test{i}"
        }
        for i in range(count)
    ]


# Environment Setup

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch, temp_dir):
    """Setup test environment variables."""
    # Set test cache directory
    monkeypatch.setenv("OSINT85_CACHE_DIR", str(temp_dir / "cache"))

    # Set test data directory
    monkeypatch.setenv("OSINT85_DATA_DIR", str(temp_dir / "data"))

    # Disable real API calls
    monkeypatch.setenv("OSINT85_MOCK_MODE", "true")

    yield


# Async Testing Helpers

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# TUI Testing Helpers

@pytest.fixture
def tui_pilot():
    """Create a Textual pilot for TUI testing."""
    from textual.pilot import Pilot
    return Pilot


# Cleanup

@pytest.fixture(autouse=True)
def cleanup_cache():
    """Cleanup global cache state between tests."""
    from osint85.cache import _cache_manager
    from osint85.perf import _profiler

    # Reset global instances
    if _cache_manager:
        _cache_manager.clear_all()

    if _profiler:
        _profiler.reset()

    yield

    # Final cleanup
    if _cache_manager:
        _cache_manager.clear_all()
