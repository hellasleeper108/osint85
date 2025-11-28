import pytest
from unittest.mock import MagicMock, patch
from osint85.command_palette import CommandPalette, CommandItem
from osint85.command_registry import Command, CommandCategory

class TestCommandPalette:
    @pytest.fixture
    def palette(self):
        palette = CommandPalette()
        # Mock the query_one method to return mock widgets
        palette.query_one = MagicMock()
        return palette

    def test_initialization(self, palette):
        assert palette.commands == []
        assert palette.filtered_commands == []

    def test_simple_search(self, palette):
        cmd1 = Command("1", "Alpha", "First letter", CommandCategory.SYSTEM, lambda: None)
        cmd2 = Command("2", "Beta", "Second letter", CommandCategory.SYSTEM, lambda: None)
        palette.commands = [cmd1, cmd2]
        
        results = palette._simple_search("Alpha")
        assert len(results) == 1
        assert results[0] == cmd1
        
        results = palette._simple_search("letter")
        assert len(results) == 2
        # Should be sorted by score, but simple check for presence
        assert cmd1 in results
        assert cmd2 in results

    def test_search_commands_empty(self, palette):
        cmd1 = Command("1", "Alpha", "First letter", CommandCategory.SYSTEM, lambda: None)
        palette.commands = [cmd1]
        
        palette._search_commands("")
        assert len(palette.filtered_commands) == 1
        assert palette.filtered_commands[0] == cmd1

    @patch('osint85.command_palette.HAS_RAPIDFUZZ', False)
    def test_search_commands_fallback(self, palette):
        cmd1 = Command("1", "Alpha", "First letter", CommandCategory.SYSTEM, lambda: None)
        palette.commands = [cmd1]
        
        # Mock _update_results since it interacts with widgets
        palette._update_results = MagicMock()
        
        palette._search_commands("Alpha")
        assert len(palette.filtered_commands) == 1
        palette._update_results.assert_called_once()

    @patch('osint85.command_palette.HAS_RAPIDFUZZ', True)
    @patch('osint85.command_palette.process')
    def test_search_commands_rapidfuzz(self, mock_process, palette):
        cmd1 = Command("1", "Alpha", "First letter", CommandCategory.SYSTEM, lambda: None)
        palette.commands = [cmd1]
        
        # Mock rapidfuzz process.extract
        mock_process.extract.return_value = [("Alpha", 100, "1")]
        
        # Mock command registry get
        with patch('osint85.command_palette.command_registry') as mock_registry:
            mock_registry.get.return_value = cmd1
            palette._update_results = MagicMock()
            
            palette._search_commands("Alpha")
            
            assert len(palette.filtered_commands) == 1
            assert palette.filtered_commands[0] == cmd1
