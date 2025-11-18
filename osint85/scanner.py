"""Search API client and result processing for osint85."""

import time
import re
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests

from .config import config
from .database import Target, Query
from .project import ProjectManager


@dataclass
class SearchResult:
    """Represents a search result."""
    url: str
    title: str
    snippet: str
    source_engine: str = ""


class SearchClient(ABC):
    """Abstract base class for search API clients."""

    @abstractmethod
    def search(self, query: str, num_results: int = 20) -> List[SearchResult]:
        """Execute a search query.

        Args:
            query: Search query string
            num_results: Maximum number of results to return

        Returns:
            List of SearchResult objects
        """
        pass


class SerpAPIClient(SearchClient):
    """SerpAPI client for Google search."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize SerpAPI client.

        Args:
            api_key: SerpAPI key (defaults to config)
        """
        self.api_key = api_key or config.SEARCH_API_KEY
        if not self.api_key:
            raise ValueError("SEARCH_API_KEY is required")

        self.base_url = "https://serpapi.com/search"

    def search(self, query: str, num_results: int = 20) -> List[SearchResult]:
        """Execute a search query via SerpAPI.

        Args:
            query: Search query string
            num_results: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        params = {
            "q": query,
            "api_key": self.api_key,
            "num": min(num_results, 100),
            "engine": "google"
        }

        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic_results", []):
                results.append(SearchResult(
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    source_engine="google"
                ))

            return results[:num_results]

        except requests.RequestException as e:
            raise RuntimeError(f"Search API error: {e}") from e


class MockSearchClient(SearchClient):
    """Mock search client for testing."""

    def search(self, query: str, num_results: int = 20) -> List[SearchResult]:
        """Return mock search results.

        Args:
            query: Search query string
            num_results: Maximum number of results

        Returns:
            List of mock SearchResult objects
        """
        # Extract domain from query if present
        domain_match = re.search(r'site:([^\s]+)', query)
        domain = domain_match.group(1) if domain_match else "example.com"

        mock_results = [
            SearchResult(
                url=f"https://{domain}/path{i}",
                title=f"Mock Result {i} for: {query[:50]}",
                snippet=f"This is a mock snippet for result {i}",
                source_engine="mock"
            )
            for i in range(min(num_results, 5))
        ]

        return mock_results


def get_search_client(provider: Optional[str] = None, mock: bool = False) -> SearchClient:
    """Get a search client instance.

    Args:
        provider: Search provider name (defaults to config)
        mock: If True, return mock client for testing

    Returns:
        SearchClient instance
    """
    if mock:
        return MockSearchClient()

    provider = provider or config.SEARCH_API_PROVIDER

    if provider == "serpapi":
        return SerpAPIClient()
    else:
        raise ValueError(f"Unsupported search provider: {provider}")


class ResultProcessor:
    """Processes and tags search results."""

    # Patterns for tagging
    BACKUP_PATTERNS = [
        r'\.bak$', r'\.backup$', r'\.old$', r'\.sql$', r'\.gz$',
        r'\.zip$', r'\.tar$', r'/backup/', r'/backups/'
    ]

    CONFIG_PATTERNS = [
        r'\.config$', r'\.conf$', r'\.ini$', r'\.env$', r'\.yaml$',
        r'\.yml$', r'/config/', r'settings\.', r'configuration'
    ]

    DEV_PATTERNS = [
        r'staging\.', r'dev\.', r'test\.', r'demo\.', r'beta\.',
        r'/staging/', r'/dev/', r'/test/', r'development'
    ]

    DEBUG_PATTERNS = [
        r'/debug/', r'phpinfo', r'stacktrace', r'error', r'exception',
        r'traceback', r'/trace'
    ]

    LOGIN_PATTERNS = [
        r'/login', r'/admin', r'/portal', r'/auth', r'/signin',
        r'/dashboard', r'wp-admin', r'administrator'
    ]

    @staticmethod
    def tag_url(url: str) -> List[str]:
        """Tag a URL based on patterns.

        Args:
            url: URL to tag

        Returns:
            List of tag strings
        """
        tags = []
        url_lower = url.lower()

        if any(re.search(pattern, url_lower) for pattern in ResultProcessor.BACKUP_PATTERNS):
            tags.append("backup")

        if any(re.search(pattern, url_lower) for pattern in ResultProcessor.CONFIG_PATTERNS):
            tags.append("config")

        if any(re.search(pattern, url_lower) for pattern in ResultProcessor.DEV_PATTERNS):
            tags.append("dev_staging")

        if any(re.search(pattern, url_lower) for pattern in ResultProcessor.DEBUG_PATTERNS):
            tags.append("debug")

        if any(re.search(pattern, url_lower) for pattern in ResultProcessor.LOGIN_PATTERNS):
            tags.append("login")

        return tags

    @staticmethod
    def score_result(result: SearchResult, tags: List[str]) -> int:
        """Score a result based on interestingness.

        Args:
            result: SearchResult object
            tags: List of tags

        Returns:
            Interest score (0-100)
        """
        score = 50  # Base score

        # High-value tags
        if "backup" in tags:
            score += 30
        if "config" in tags:
            score += 25
        if "debug" in tags:
            score += 20
        if "login" in tags:
            score += 15
        if "dev_staging" in tags:
            score += 10

        # Snippet keywords
        snippet_lower = result.snippet.lower()
        if any(keyword in snippet_lower for keyword in ["password", "secret", "key", "token"]):
            score += 20
        if "index of" in snippet_lower:
            score += 15

        return min(score, 100)


class Scanner:
    """Executes search queries and processes results."""

    def __init__(self, project_manager: ProjectManager, search_client: Optional[SearchClient] = None,
                 mock: bool = False):
        """Initialize scanner.

        Args:
            project_manager: ProjectManager instance
            search_client: SearchClient instance (defaults to config provider)
            mock: Use mock search client for testing
        """
        self.pm = project_manager
        self.search_client = search_client or get_search_client(mock=mock)
        self.processor = ResultProcessor()

    def run(self, target: Target, queries: List[Query], max_results: int = 20, delay: float = 1.0):
        """Run search queries and save results.

        Args:
            target: Target object
            queries: List of Query objects to execute
            max_results: Maximum results per query
            delay: Delay between queries in seconds (rate limiting)
        """
        total_queries = len(queries)
        total_results = 0

        for i, query in enumerate(queries, 1):
            print(f"[{i}/{total_queries}] Running query: {query.description}")
            print(f"  Query: {query.query}")

            try:
                # Execute search
                results = self.search_client.search(query.query, num_results=max_results)
                print(f"  Found {len(results)} results")

                # Process and save results
                for result in results:
                    # Tag the result
                    tags = self.processor.tag_url(result.url)
                    tags_str = ",".join(tags) if tags else ""

                    # Save to database
                    self.pm.save_result(
                        query_id=query.id,
                        url=result.url,
                        title=result.title,
                        snippet=result.snippet,
                        source_engine=result.source_engine,
                        tags=tags_str
                    )
                    total_results += 1

                # Rate limiting delay
                if i < total_queries:
                    time.sleep(delay)

            except Exception as e:
                print(f"  [ERROR] Query failed: {e}")
                continue

        print(f"\nScan complete: {total_results} results from {total_queries} queries")

    def run_single_query(self, query: Query, max_results: int = 20) -> List[SearchResult]:
        """Run a single query and return results (without saving).

        Args:
            query: Query object
            max_results: Maximum results to return

        Returns:
            List of SearchResult objects
        """
        return self.search_client.search(query.query, num_results=max_results)
