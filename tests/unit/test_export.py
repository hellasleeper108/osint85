import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from osint85.export import MarkdownExporter, JSONExporter, HTMLExporter, Exporter
from osint85.database import Result, Query, Target

class TestExporter:
    @pytest.fixture
    def mock_pm(self):
        return MagicMock()

    @pytest.fixture
    def sample_data(self):
        target = Target(id=1, name="Test Target", primary_domain="example.com", created_at="now")
        query = Query(id=1, target_id=1, category="test", risk_level="high", 
                      description="Test Query", query="site:example.com", enabled=True, created_at="now")
        result = Result(id=1, query_id=1, url="http://example.com", title="Example", 
                        snippet="Snippet", source_engine="google", tags="tag1", 
                        first_seen_at="now", last_seen_at="now")
        return target, query, result

    def test_sanitize_filename(self):
        exporter = Exporter()
        assert exporter._sanitize_filename("test/file:name") == "test_file_name"
        assert exporter._sanitize_filename("test file") == "test_file"

    def test_markdown_export_result(self, mock_pm, sample_data):
        target, query, result = sample_data
        exporter = MarkdownExporter(mock_pm)
        
        with patch("builtins.open", mock_open()) as mock_file:
            path = exporter.export_result(result, query, "test")
            
            assert isinstance(path, Path)
            mock_file.assert_called_once()
            handle = mock_file()
            handle.write.assert_called_once()
            args = handle.write.call_args[0]
            assert "# OSINT-85 Result Export" in args[0]

    def test_json_export_result(self, mock_pm, sample_data):
        target, query, result = sample_data
        exporter = JSONExporter(mock_pm)
        
        with patch("builtins.open", mock_open()) as mock_file:
            path = exporter.export_result(result, query, "test")
            
            mock_file.assert_called_once()
            handle = mock_file()
            handle.write.assert_called() # JSON dump writes multiple times

    def test_html_export_result(self, mock_pm, sample_data):
        target, query, result = sample_data
        exporter = HTMLExporter(mock_pm)
        
        with patch("builtins.open", mock_open()) as mock_file:
            path = exporter.export_result(result, query, "test")
            
            mock_file.assert_called_once()
            handle = mock_file()
            handle.write.assert_called_once()
            args = handle.write.call_args[0]
            assert "<!DOCTYPE html>" in args[0]

    def test_markdown_export_project(self, mock_pm, sample_data):
        target, query, result = sample_data
        mock_pm.list_queries.return_value = [query]
        mock_pm.get_results_by_query.return_value = [result]
        
        exporter = MarkdownExporter(mock_pm)
        
        with patch("builtins.open", mock_open()) as mock_file:
            path = exporter.export_project(target)
            
            mock_file.assert_called_once()
            handle = mock_file()
            handle.write.assert_called_once()
            args = handle.write.call_args[0]
            assert "# OSINT-85 Full Project Report" in args[0]
