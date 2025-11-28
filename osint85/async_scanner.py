"""Async scanning engine for real-time result streaming."""

import asyncio
import time
from typing import List, Dict, Any, Optional, AsyncIterator, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import httpx

from .config import config
from .database import Target, Query, Result
from .project import ProjectManager
from .scanner import SearchResult, ResultProcessor


class ScanStatus(Enum):
    """Status of a scan task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScanProgress:
    """Progress update from a scan task."""
    query_id: int
    query_description: str
    status: ScanStatus
    results_count: int = 0
    error: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class LiveResult:
    """A result yielded during live scanning."""
    query_id: int
    category: str
    url: str
    title: str
    snippet: str
    source_engine: str
    tags: str
    score: int
    timestamp: str


class AsyncSearchClient:
    """Async search client base class."""

    async def search_async(self, query: str, num_results: int = 20) -> List[SearchResult]:
        """Execute an async search query.

        Args:
            query: Search query string
            num_results: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        raise NotImplementedError


class AsyncSerpAPIClient(AsyncSearchClient):
    """Async SerpAPI client for Google search."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize async SerpAPI client.

        Args:
            api_key: SerpAPI key (defaults to config)
        """
        self.api_key = api_key or config.SEARCH_API_KEY
        if not self.api_key:
            raise ValueError("SEARCH_API_KEY is required")

        self.base_url = "https://serpapi.com/search"

    async def search_async(self, query: str, num_results: int = 20) -> List[SearchResult]:
        """Execute an async search query via SerpAPI.

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

        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            try:
                response = await client.get(self.base_url, params=params)
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

            except httpx.HTTPError as e:
                raise RuntimeError(f"Search API error: {e}") from e


class AsyncMockSearchClient(AsyncSearchClient):
    """Async mock search client for testing."""

    async def search_async(self, query: str, num_results: int = 20) -> List[SearchResult]:
        """Return mock search results asynchronously.

        Args:
            query: Search query string
            num_results: Maximum number of results

        Returns:
            List of mock SearchResult objects
        """
        # Simulate network delay
        await asyncio.sleep(0.5 + (hash(query) % 10) / 10)

        # Extract domain from query if present
        import re
        domain_match = re.search(r'site:([^\s]+)', query)
        domain = domain_match.group(1) if domain_match else "example.com"

        # Generate varied mock results
        categories = ["backup", "config", "staging", "admin", "debug"]
        paths = ["data", "files", "uploads", "assets", "public"]

        mock_results = []
        for i in range(min(num_results, 5)):
            cat = categories[i % len(categories)]
            path = paths[i % len(paths)]

            mock_results.append(SearchResult(
                url=f"https://{domain}/{cat}/{path}/item{i}.html",
                title=f"{cat.title()} Resource {i} - {query[:30]}",
                snippet=f"Mock snippet for {cat} result {i}. This could contain sensitive information.",
                source_engine="mock"
            ))

        return mock_results


class ScanTaskRunner:
    """Async task runner for scanning operations."""

    def __init__(self, project_manager: ProjectManager, search_client: Optional[AsyncSearchClient] = None,
                 mock: bool = False):
        """Initialize scan task runner.

        Args:
            project_manager: ProjectManager instance
            search_client: AsyncSearchClient instance (defaults to mock)
            mock: Use mock search client for testing
        """
        self.pm = project_manager
        self.search_client = search_client or (AsyncMockSearchClient() if mock else AsyncSerpAPIClient())
        self.processor = ResultProcessor()
        self._cancelled = False

    async def run_live_scan(
        self,
        target: Target,
        queries: List[Query],
        max_results: int = 20,
        delay: float = 1.0
    ) -> AsyncIterator[Union[LiveResult, ScanProgress]]:
        """Run queries and yield results incrementally.

        Args:
            target: Target object
            queries: List of Query objects to execute
            max_results: Maximum results per query
            delay: Delay between queries in seconds

        Yields:
            LiveResult or ScanProgress objects
        """
        total_queries = len(queries)
        total_results = 0
        start_time = time.time()

        for i, query in enumerate(queries, 1):
            if self._cancelled:
                yield ScanProgress(
                    query_id=query.id,
                    query_description=query.description,
                    status=ScanStatus.CANCELLED,
                    timestamp=datetime.now().isoformat()
                )
                break

            # Notify query start
            yield ScanProgress(
                query_id=query.id,
                query_description=query.description,
                status=ScanStatus.RUNNING,
                results_count=0,
                timestamp=datetime.now().isoformat()
            )

            try:
                # Execute async search
                results = await self.search_client.search_async(query.query, num_results=max_results)

                # Process and yield results one by one
                for result in results:
                    if self._cancelled:
                        break

                    # Tag and score the result
                    tags = self.processor.tag_url(result.url)
                    tags_str = ",".join(tags) if tags else ""
                    score = self.processor.score_result(result, tags)

                    # Save to database
                    self.pm.save_result(
                        query_id=query.id,
                        url=result.url,
                        title=result.title,
                        snippet=result.snippet,
                        source_engine=result.source_engine,
                        tags=tags_str
                    )

                    # Yield live result
                    yield LiveResult(
                        query_id=query.id,
                        category=query.category,
                        url=result.url,
                        title=result.title,
                        snippet=result.snippet,
                        source_engine=result.source_engine,
                        tags=tags_str,
                        score=score,
                        timestamp=datetime.now().isoformat()
                    )

                    total_results += 1

                # Notify query completion
                yield ScanProgress(
                    query_id=query.id,
                    query_description=query.description,
                    status=ScanStatus.COMPLETED,
                    results_count=len(results),
                    timestamp=datetime.now().isoformat()
                )

                # Rate limiting delay
                if i < total_queries and not self._cancelled:
                    await asyncio.sleep(delay)

            except Exception as e:
                # Notify query failure
                yield ScanProgress(
                    query_id=query.id,
                    query_description=query.description,
                    status=ScanStatus.FAILED,
                    error=str(e),
                    timestamp=datetime.now().isoformat()
                )

        # Final summary
        elapsed = time.time() - start_time
        if not self._cancelled:
            yield ScanProgress(
                query_id=0,
                query_description=f"Scan completed: {total_results} results from {total_queries} queries in {elapsed:.1f}s",
                status=ScanStatus.COMPLETED,
                results_count=total_results,
                timestamp=datetime.now().isoformat()
            )

    async def run_category_scan(
        self,
        target: Target,
        category: str,
        max_results: int = 20,
        delay: float = 1.0
    ) -> AsyncIterator[Union[LiveResult, ScanProgress]]:
        """Run all enabled queries for a category.

        Args:
            target: Target object
            category: Category ID to scan
            max_results: Maximum results per query
            delay: Delay between queries in seconds

        Yields:
            LiveResult or ScanProgress objects
        """
        # Get enabled queries for this category
        queries = self.pm.get_enabled_queries(target.id)
        category_queries = [q for q in queries if q.category == category]

        if not category_queries:
            yield ScanProgress(
                query_id=0,
                query_description=f"No enabled queries for category: {category}",
                status=ScanStatus.FAILED,
                timestamp=datetime.now().isoformat()
            )
            return

        # Run the scan
        async for item in self.run_live_scan(target, category_queries, max_results, delay):
            yield item

    def cancel(self):
        """Cancel the current scan."""
        self._cancelled = True

    def reset(self):
        """Reset cancellation flag."""
        self._cancelled = False


async def get_async_search_client(provider: Optional[str] = None, mock: bool = False) -> AsyncSearchClient:
    """Get an async search client instance.

    Args:
        provider: Search provider name (defaults to config)
        mock: If True, return mock client for testing

    Returns:
        AsyncSearchClient instance
    """
    if mock:
        return AsyncMockSearchClient()

    provider = provider or config.SEARCH_API_PROVIDER

    if provider == "serpapi":
        return AsyncSerpAPIClient()
    else:
        raise ValueError(f"Unsupported search provider: {provider}")
