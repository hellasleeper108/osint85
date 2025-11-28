import pytest
from unittest.mock import MagicMock, patch, AsyncMock, PropertyMock
from osint85.result_detail_view import ResultDetailView
from osint85.database import Result

class TestResultDetailView:
    @pytest.fixture
    def result(self):
        return Result(
            id=1, query_id=1, url="http://example.com", title="Example", 
            snippet="Snippet", source_engine="google", tags="tag1,high-risk", 
            first_seen_at="now", last_seen_at="now"
        )

    def test_initialization(self, result):
        view = ResultDetailView(result, "query desc", "category")
        assert view.result == result
        assert view.query_description == "query desc"
        assert view.category == "category"

    def test_format_tags(self, result):
        view = ResultDetailView(result)
        formatted = view._format_tags("tag1, high-risk")
        assert "#tag1" in formatted
        assert "[red]#high-risk[/red]" in formatted

    def test_format_timestamps(self, result):
        view = ResultDetailView(result)
        formatted = view._format_timestamps()
        assert "First seen" in formatted
        assert "now" in formatted

    def test_format_scoring(self, result):
        view = ResultDetailView(result)
        scoring = view._format_scoring()
        assert "High-risk tag applied" in scoring

    @pytest.mark.asyncio
    async def test_action_summarize(self, result):
        view = ResultDetailView(result)
        view.query_one = MagicMock()
        
        # Patch the app property on the class
        with patch('osint85.result_detail_view.ResultDetailView.app', new_callable=PropertyMock) as mock_app_prop:
            mock_app = MagicMock()
            mock_app_prop.return_value = mock_app
            
        with patch('osint85.llm_client.get_llm_client') as mock_get_client:
                mock_client = MagicMock()
                mock_client.generate_async = AsyncMock(return_value="Summary")
                mock_get_client.return_value = mock_client
                
                await view.action_summarize()
                
                mock_client.generate_async.assert_called_once()
                view.query_one.assert_called()

    @pytest.mark.asyncio
    async def test_action_export(self, result):
        view = ResultDetailView(result)
        
        with patch('osint85.result_detail_view.ResultDetailView.app', new_callable=PropertyMock) as mock_app_prop:
            mock_app = MagicMock()
            mock_app_prop.return_value = mock_app
            
            with patch('osint85.export.get_exporter') as mock_get_exporter, \
                 patch('osint85.project.ProjectManager') as MockPM:
                mock_exporter = MagicMock()
                mock_get_exporter.return_value = mock_exporter
                
                await view.action_export()
                
                assert mock_exporter.export_result.call_count >= 1
