"""Command Palette widget for OSINT-85."""

from typing import List, Optional
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, ListView, ListItem, Label, Static
from textual.containers import Container, Vertical
from textual.binding import Binding
from textual import events

from .command_registry import Command, command_registry

# Try to import rapidfuzz for better fuzzy matching
try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


class CommandItem(ListItem):
    """A command item in the palette list."""

    def __init__(self, command: Command):
        super().__init__()
        self.command = command

    def compose(self) -> ComposeResult:
        """Compose the command item."""
        # Format keybinding if present
        keybinding = f"  [{self.command.keybinding}]" if self.command.keybinding else ""

        # Create the display
        yield Static(
            f"[bold cyan]{self.command.name}[/bold cyan]{keybinding}\n"
            f"[dim]{self.command.description}[/dim]",
            classes="command-item-content"
        )


class CommandPalette(ModalScreen):
    """Command Palette modal for quick command access."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("ctrl+c", "dismiss", "Close", show=False),
    ]

    DEFAULT_CSS = """
    CommandPalette {
        align: center middle;
    }

    #palette-container {
        width: 70;
        height: auto;
        max-height: 35;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #palette-title {
        text-style: bold;
        color: $primary;
        background: $surface-darken-1;
        padding: 1;
        margin-bottom: 1;
        text-align: center;
    }

    #palette-input {
        margin-bottom: 1;
        border: tall $primary-darken-1;
    }

    #palette-input:focus {
        border: tall $primary;
    }

    #palette-results {
        height: auto;
        max-height: 20;
        border: tall $surface-lighten-1;
        background: $surface-darken-1;
    }

    #no-results {
        padding: 2;
        text-align: center;
        color: $text-muted;
    }

    .command-item-content {
        padding: 1;
    }

    CommandItem {
        height: auto;
        padding: 0;
    }

    CommandItem:hover {
        background: $surface-lighten-1;
    }

    CommandItem.-active {
        background: $accent;
    }
    """

    def __init__(self):
        super().__init__()
        self.commands: List[Command] = []
        self.filtered_commands: List[Command] = []

    def compose(self) -> ComposeResult:
        """Compose the palette UI."""
        with Container(id="palette-container"):
            yield Static("⚡ COMMAND PALETTE", id="palette-title")
            yield Input(
                placeholder="Type to search commands...",
                id="palette-input"
            )
            yield ListView(id="palette-results")
            yield Static("No commands found", id="no-results", classes="hidden")

    def on_mount(self):
        """Initialize the palette on mount."""
        # Load all commands
        self.commands = command_registry.all_commands()
        self.filtered_commands = self.commands.copy()

        # Focus the input
        input_widget = self.query_one("#palette-input", Input)
        input_widget.focus()

        # Populate initial results
        self._update_results()

    def on_input_changed(self, event: Input.Changed):
        """Handle input changes for search."""
        if event.input.id == "palette-input":
            self._search_commands(event.value)

    def _search_commands(self, query: str):
        """Search commands with fuzzy matching.

        Args:
            query: Search query
        """
        if not query:
            # Show all commands if no query
            self.filtered_commands = self.commands.copy()
        else:
            # Fuzzy search
            if HAS_RAPIDFUZZ:
                # Use rapidfuzz for better matching
                self.filtered_commands = self._fuzzy_search_rapidfuzz(query)
            else:
                # Fallback to simple substring matching
                self.filtered_commands = self._simple_search(query)

        self._update_results()

    def _fuzzy_search_rapidfuzz(self, query: str, limit: int = 15) -> List[Command]:
        """Fuzzy search using rapidfuzz.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching commands
        """
        # Create list of searchable strings
        choices = {cmd.id: cmd.search_text for cmd in self.commands}

        # Use rapidfuzz to find best matches
        results = process.extract(
            query.lower(),
            choices,
            scorer=fuzz.WRatio,
            limit=limit
        )

        # Get command objects for matches
        matched_commands = []
        for match_text, score, cmd_id in results:
            if score > 40:  # Minimum score threshold
                cmd = command_registry.get(cmd_id)
                if cmd:
                    matched_commands.append(cmd)

        return matched_commands

    def _simple_search(self, query: str, limit: int = 15) -> List[Command]:
        """Simple substring search fallback.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching commands
        """
        query_lower = query.lower()
        matches = []

        for cmd in self.commands:
            # Score based on where match occurs
            name_lower = cmd.name.lower()
            desc_lower = cmd.description.lower()

            score = 0
            if query_lower in name_lower:
                # Prioritize name matches
                if name_lower.startswith(query_lower):
                    score = 100  # Exact prefix match
                else:
                    score = 70  # Substring match in name
            elif query_lower in desc_lower:
                score = 50  # Match in description
            elif query_lower in cmd.search_text:
                score = 30  # Match in keywords/category

            if score > 0:
                matches.append((score, cmd))

        # Sort by score and return
        matches.sort(key=lambda x: x[0], reverse=True)
        return [cmd for score, cmd in matches[:limit]]

    def _update_results(self):
        """Update the results list."""
        results_list = self.query_one("#palette-results", ListView)
        no_results = self.query_one("#no-results", Static)

        # Clear existing results
        results_list.clear()

        if not self.filtered_commands:
            # Show no results message
            no_results.remove_class("hidden")
            results_list.add_class("hidden")
        else:
            # Show results
            no_results.add_class("hidden")
            results_list.remove_class("hidden")

            # Add command items
            for cmd in self.filtered_commands:
                results_list.append(CommandItem(cmd))

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle command selection."""
        if isinstance(event.item, CommandItem):
            command = event.item.command
            self.dismiss(command)

    def on_key(self, event: events.Key):
        """Handle key events."""
        if event.key == "enter":
            # Execute selected command
            results_list = self.query_one("#palette-results", ListView)
            if results_list.highlighted_child:
                if isinstance(results_list.highlighted_child, CommandItem):
                    command = results_list.highlighted_child.command
                    self.dismiss(command)
                    event.prevent_default()
        elif event.key == "down" or event.key == "up":
            # Navigate results with arrow keys
            results_list = self.query_one("#palette-results", ListView)
            results_list.focus()


# Helper function to show the palette
async def show_command_palette(app) -> Optional[Command]:
    """Show the command palette and return selected command.

    Args:
        app: The Textual app instance

    Returns:
        Selected command or None if dismissed
    """
    result = await app.push_screen(CommandPalette())
    return result if isinstance(result, Command) else None
