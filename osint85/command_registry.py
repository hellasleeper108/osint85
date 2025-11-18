"""Command registry for OSINT-85 Command Palette."""

from typing import Callable, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum


class CommandCategory(Enum):
    """Command categories for organization."""
    PROJECT = "project"
    QUERY = "query"
    SCAN = "scan"
    REPORT = "report"
    NAVIGATION = "navigation"
    VIEW = "view"
    SYSTEM = "system"
    PLUGIN = "plugin"


@dataclass
class Command:
    """Represents a palette command."""
    id: str
    name: str
    description: str
    category: CommandCategory
    action: Callable
    keywords: List[str] = None
    keybinding: Optional[str] = None

    def __post_init__(self):
        """Initialize keywords if not provided."""
        if self.keywords is None:
            self.keywords = []

    @property
    def search_text(self) -> str:
        """Get searchable text for this command."""
        parts = [self.name, self.description, self.category.value]
        parts.extend(self.keywords)
        if self.keybinding:
            parts.append(self.keybinding)
        return " ".join(parts).lower()


class CommandRegistry:
    """Global registry for command palette commands."""

    _instance = None
    _commands: Dict[str, Command] = {}

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._commands = {}
        return cls._instance

    def register(
        self,
        command_id: str,
        name: str,
        description: str,
        action: Callable,
        category: CommandCategory = CommandCategory.SYSTEM,
        keywords: List[str] = None,
        keybinding: Optional[str] = None
    ):
        """Register a new command.

        Args:
            command_id: Unique identifier for the command
            name: Display name
            description: Description shown in palette
            action: Callable to execute when command is selected
            category: Command category for organization
            keywords: Additional search keywords
            keybinding: Optional keyboard shortcut display
        """
        command = Command(
            id=command_id,
            name=name,
            description=description,
            category=category,
            action=action,
            keywords=keywords or [],
            keybinding=keybinding
        )
        self._commands[command_id] = command

    def unregister(self, command_id: str):
        """Unregister a command.

        Args:
            command_id: Command ID to remove
        """
        if command_id in self._commands:
            del self._commands[command_id]

    def get(self, command_id: str) -> Optional[Command]:
        """Get a command by ID.

        Args:
            command_id: Command ID

        Returns:
            Command if found, None otherwise
        """
        return self._commands.get(command_id)

    def all_commands(self) -> List[Command]:
        """Get all registered commands.

        Returns:
            List of all commands
        """
        return list(self._commands.values())

    def commands_by_category(self, category: CommandCategory) -> List[Command]:
        """Get commands in a specific category.

        Args:
            category: Category to filter by

        Returns:
            List of commands in category
        """
        return [cmd for cmd in self._commands.values() if cmd.category == category]

    def search(self, query: str, limit: int = 10) -> List[Command]:
        """Search commands (basic implementation, enhanced by palette).

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching commands
        """
        if not query:
            return self.all_commands()[:limit]

        query_lower = query.lower()
        matches = [
            cmd for cmd in self._commands.values()
            if query_lower in cmd.search_text
        ]
        return matches[:limit]

    def clear(self):
        """Clear all registered commands."""
        self._commands.clear()


# Global registry instance
command_registry = CommandRegistry()
