import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from osint85.async_db import AsyncDatabase
from osint85.database import Query, Result

@pytest.mark.asyncio
class TestAsyncDatabase:
    async def test_connect_close(self):
        with patch('osint85.async_db.aiosqlite.connect', new_callable=AsyncMock) as mock_connect:
            mock_db = AsyncMock()
            mock_connect.return_value = mock_db
            
            async_db = AsyncDatabase(":memory:")
            await async_db.connect()
            
            mock_connect.assert_called_once_with(":memory:")
            assert async_db._conn == mock_db
            
            await async_db.close()
            mock_db.close.assert_called_once()
            assert async_db._conn is None

    async def test_context_manager(self):
        with patch('osint85.async_db.aiosqlite.connect', new_callable=AsyncMock) as mock_connect:
            mock_db = AsyncMock()
            mock_connect.return_value = mock_db
            
            async with AsyncDatabase(":memory:") as db:
                mock_connect.assert_called_once_with(":memory:")
                assert db._conn == mock_db
            
            mock_db.close.assert_called_once()

    async def test_get_queries_by_category_async(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock row data
        row_data = {
            'id': 1,
            'target_id': 1,
            'category': 'test',
            'risk_level': 'high',
            'description': 'desc',
            'query': 'query',
            'enabled': 1,
            'created_at': '2023-01-01'
        }
        mock_cursor.fetchall.return_value = [row_data]
        
        async_db = AsyncDatabase()
        async_db._conn = mock_conn
        
        queries = await async_db.get_queries_by_category_async(1, 'test')
        
        assert len(queries) == 1
        assert isinstance(queries[0], Query)
        assert queries[0].id == 1
        
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()

    async def test_get_all_queries_async(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value = mock_cursor
        
        row_data = {
            'id': 1,
            'target_id': 1,
            'category': 'test',
            'risk_level': 'high',
            'description': 'desc',
            'query': 'query',
            'enabled': 1,
            'created_at': '2023-01-01'
        }
        mock_cursor.fetchall.return_value = [row_data]
        
        async_db = AsyncDatabase()
        async_db._conn = mock_conn
        
        queries = await async_db.get_all_queries_async(1)
        
        assert len(queries) == 1
        assert queries[0].target_id == 1

    async def test_get_results_by_query_async(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value = mock_cursor
        
        row_data = {
            'id': 1,
            'query_id': 1,
            'url': 'http://example.com',
            'title': 'Example',
            'snippet': 'Snippet',
            'source_engine': 'google',
            'tags': 'tag1',
            'first_seen_at': '2023-01-01',
            'last_seen_at': '2023-01-01',
            'is_duplicate': 0,
            'duplicate_of_id': None,
            'similarity_score': None
        }
        mock_cursor.fetchall.return_value = [row_data]
        
        async_db = AsyncDatabase()
        async_db._conn = mock_conn
        
        results = await async_db.get_results_by_query_async(1)
        
        assert len(results) == 1
        assert isinstance(results[0], Result)
        assert results[0].url == 'http://example.com'

    async def test_count_results_async(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (5,)
        
        async_db = AsyncDatabase()
        async_db._conn = mock_conn
        
        count = await async_db.count_results_async(1)
        
        assert count == 5
