import pytest
from osint85.command_registry import CommandRegistry, Command, CommandCategory

class TestCommandRegistry:
    @pytest.fixture(autouse=True)
    def setup_registry(self):
        self.registry = CommandRegistry()
        self.registry.clear()
        yield
        self.registry.clear()

    def test_singleton(self):
        registry1 = CommandRegistry()
        registry2 = CommandRegistry()
        assert registry1 is registry2

    def test_register_command(self):
        def dummy_action():
            pass

        self.registry.register(
            command_id="test.cmd",
            name="Test Command",
            description="A test command",
            action=dummy_action,
            category=CommandCategory.SYSTEM
        )

        cmd = self.registry.get("test.cmd")
        assert cmd is not None
        assert cmd.name == "Test Command"
        assert cmd.category == CommandCategory.SYSTEM

    def test_unregister_command(self):
        self.registry.register(
            command_id="test.cmd",
            name="Test Command",
            description="A test command",
            action=lambda: None
        )
        
        self.registry.unregister("test.cmd")
        assert self.registry.get("test.cmd") is None

    def test_all_commands(self):
        self.registry.register("cmd1", "Cmd1", "Desc1", lambda: None)
        self.registry.register("cmd2", "Cmd2", "Desc2", lambda: None)
        
        cmds = self.registry.all_commands()
        assert len(cmds) == 2

    def test_commands_by_category(self):
        self.registry.register(
            "cmd1", "Cmd1", "Desc1", lambda: None, category=CommandCategory.SYSTEM
        )
        self.registry.register(
            "cmd2", "Cmd2", "Desc2", lambda: None, category=CommandCategory.PROJECT
        )
        
        system_cmds = self.registry.commands_by_category(CommandCategory.SYSTEM)
        assert len(system_cmds) == 1
        assert system_cmds[0].id == "cmd1"

    def test_search(self):
        self.registry.register(
            "cmd1", "Find Me", "Description", lambda: None, keywords=["searchable"]
        )
        self.registry.register(
            "cmd2", "Hidden", "Description", lambda: None
        )
        
        results = self.registry.search("Find")
        assert len(results) == 1
        assert results[0].id == "cmd1"
        
        results = self.registry.search("searchable")
        assert len(results) == 1
        assert results[0].id == "cmd1"
