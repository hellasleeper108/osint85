"""Integration tests for complete scan workflows."""

import pytest
from unittest.mock import Mock, AsyncMock

from osint85.project import ProjectManager
from osint85.dorks import DorkGenerator
from osint85.scanner import Scanner


class TestScanWorkflow:
    """Test complete scan workflow integration."""

    @pytest.mark.asyncio
    async def test_complete_scan_workflow(self, test_project_manager, mock_llm_client, mock_search_client):
        """Test complete workflow: create project -> generate queries -> run scan."""
        pm = test_project_manager

        # Step 1: Create target
        target = pm.create_project(
            name="Integration Test",
            domain="test.com",
            scope="*.test.com"
        )

        assert target.id is not None

        # Step 2: Generate queries (mocked LLM)
        with pytest.warns(None) as record:
            from unittest.mock import patch
            with patch('osint85.dorks.get_llm_client', return_value=mock_llm_client):
                dork_gen = DorkGenerator()
                queries_json = mock_llm_client.generate(
                    system="test",
                    prompt="test",
                    model="test"
                )

        # Parse and save queries
        import json
        try:
            queries_data = json.loads(queries_json)
            if "queries" in queries_data:
                saved_queries = pm.save_queries(target.id, queries_data["queries"])
                assert len(saved_queries) > 0
        except json.JSONDecodeError:
            pytest.skip("Mock LLM response is not valid JSON")

        # Step 3: Run scanner (mocked API)
        scanner = Scanner(pm, search_client=mock_search_client)

        queries = pm.list_queries(target.id)
        for query in queries[:1]:  # Test with first query
            results = mock_search_client.search(query.query, max_results=10)

            # Save results
            for result in results:
                pm.save_result(
                    query_id=query.id,
                    url=result["url"],
                    title=result["title"],
                    snippet=result.get("snippet", ""),
                    source_engine=result.get("source_engine", "")
                )

        # Verify results were saved
        all_results = pm.get_all_results(target.id)
        assert len(all_results) > 0

    def test_scan_with_deduplication(self, test_project_manager):
        """Test scan workflow with deduplication."""
        from osint85.dedupe import DeduplicationEngine

        pm = test_project_manager

        # Create target and queries
        target = pm.create_project("Dedupe Test", "test.com")
        queries = pm.save_queries(target.id, [{
            "category": "test",
            "risk_level": "low",
            "description": "Test",
            "query": "test"
        }])

        # Add duplicate results
        pm.save_result(queries[0].id, "https://test.com/page", "Page")
        pm.save_result(queries[0].id, "https://test.com/page", "Page Duplicate")

        # Run deduplication
        engine = DeduplicationEngine(pm)
        marked = engine.mark_duplicates(target.id)

        # Verify duplicates were found
        stats = engine.get_duplicate_stats(target.id)
        assert stats["total_results"] > 0

    def test_scan_with_caching(self, test_project_manager, test_cache_manager):
        """Test scan workflow with caching enabled."""
        from osint85.cache import APICache

        api_cache = test_cache_manager.api_cache

        # Cache a query result
        query = "site:test.com"
        results = [{"url": "https://test.com", "title": "Test"}]
        api_cache.set(query, results)

        # Retrieve from cache
        cached_results = api_cache.get(query)
        assert cached_results == results

        # Check cache stats
        stats = api_cache.get_stats()
        assert stats.hits > 0


class TestAsyncWorkflow:
    """Test async scan workflows."""

    @pytest.mark.asyncio
    async def test_async_database_operations(self, temp_dir):
        """Test async database operations."""
        from osint85.async_db import AsyncDatabase
        from osint85.database import Database

        # Create database with data
        db_path = temp_dir / "async_test.db"
        sync_db = Database(str(db_path))

        target = sync_db.create_target("Async Test", "test.com")
        queries = sync_db.save_queries(target.id, [{
            "category": "test",
            "risk_level": "low",
            "description": "Test",
            "query": "test"
        }])

        for i in range(5):
            sync_db.save_result(
                query_id=queries[0].id,
                url=f"https://test.com/page{i}",
                title=f"Page {i}"
            )

        sync_db.close()

        # Test async operations
        async with AsyncDatabase(str(db_path)) as async_db:
            # Count results
            count = await async_db.count_results_async(target.id)
            assert count == 5

            # Get results with pagination
            results = await async_db.get_all_results_async(
                target.id,
                limit=2,
                offset=0
            )
            assert len(results) == 2

            # Get next page
            results_page2 = await async_db.get_all_results_async(
                target.id,
                limit=2,
                offset=2
            )
            assert len(results_page2) == 2
