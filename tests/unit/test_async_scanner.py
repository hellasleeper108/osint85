import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from osint85.async_scanner import (
    AsyncSerpAPIClient, 
    AsyncMockSearchClient, 
    ScanTaskRunner, 
    ScanStatus,
    ScanProgress,
    LiveResult
)
from osint85.scanner import SearchResult
from osint85.database import Target, Query

@pytest.mark.asyncio
class TestAsyncSerpAPIClient:
    async def test_init_error(self):
        with patch('osint85.config.config.SEARCH_API_KEY', None):
            with pytest.raises(ValueError, match="SEARCH_API_KEY is required"):
                AsyncSerpAPIClient()

    async def test_search_async_success(self):
        client = AsyncSerpAPIClient(api_key="test_key")
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "organic_results": [
                {"link": "http://example.com", "title": "Example", "snippet": "Snippet"}
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            
            results = await client.search_async("query")
            
            assert len(results) == 1
            assert results[0].url == "http://example.com"

@pytest.mark.asyncio
class TestAsyncMockSearchClient:
    async def test_search_async(self):
        client = AsyncMockSearchClient()
        results = await client.search_async("test query", num_results=5)
        
        assert len(results) == 5
        assert results[0].source_engine == "mock"

@pytest.mark.asyncio
class TestScanTaskRunner:
    @pytest.fixture
    def runner(self):
        mock_pm = MagicMock()
        mock_client = AsyncMockSearchClient()
        return ScanTaskRunner(mock_pm, search_client=mock_client)

    async def test_run_live_scan(self, runner):
        target = Target(id=1, name="test", primary_domain="example.com", created_at="now")
        queries = [
            Query(id=1, target_id=1, category="test", risk_level="high", 
                  description="desc", query="query", enabled=True, created_at="now")
        ]
        
        results = []
        async for item in runner.run_live_scan(target, queries):
            results.append(item)
            
        # Should yield: start progress, result(s), end query progress, final summary
        assert len(results) > 0
        assert any(isinstance(r, ScanProgress) and r.status == ScanStatus.RUNNING for r in results)
        assert any(isinstance(r, LiveResult) for r in results)
        assert any(isinstance(r, ScanProgress) and r.status == ScanStatus.COMPLETED for r in results)

    async def test_cancel_scan(self, runner):
        target = Target(id=1, name="test", primary_domain="example.com", created_at="now")
        queries = [
            Query(id=1, target_id=1, category="test", risk_level="high", 
                  description="desc", query="query", enabled=True, created_at="now")
        ]
        
        runner.cancel()
        results = []
        async for item in runner.run_live_scan(target, queries):
            results.append(item)
            
        assert len(results) == 1
        assert results[0].status == ScanStatus.CANCELLED
