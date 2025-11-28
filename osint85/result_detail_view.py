"""Result Detail View widget for displaying comprehensive result information."""

from datetime import datetime
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static
from textual.binding import Binding
from rich.text import Text

from .database import Result


class ResultDetailView(ModalScreen):
    """Modal view for displaying detailed result information."""

    BINDINGS = [
        Binding("q", "dismiss", "Close", show=True),
        Binding("escape", "dismiss", "Close", show=False),
        Binding("s", "summarize", "Summarize", show=True),
        Binding("e", "export", "Export", show=True),
    ]

    DEFAULT_CSS = """
    ResultDetailView {
        align: center middle;
    }
    """

    def __init__(self, result: Result, query_description: str = "", category: str = ""):
        """Initialize the detail view.

        Args:
            result: The Result object to display
            query_description: Description of the query that generated this result
            category: Category of the query (e.g., "exposed_backups")
        """
        super().__init__()
        self.result = result
        self.query_description = query_description
        self.category = category

    def compose(self) -> ComposeResult:
        """Compose the detail view layout."""
        with Container(id="detail-container"):
            yield Static("🔍 RESULT DETAILS", id="detail-title")

            with ScrollableContainer(id="detail-content"):
                # URL Section
                yield Label("🔗 URL", classes="field-label")
                yield Static(self.result.url, classes="field-value url-value")

                # Title Section
                yield Label("📋 Title", classes="field-label")
                yield Static(self.result.title or "[dim]No title[/dim]", classes="field-value")

                # Snippet Section
                yield Label("📝 Snippet", classes="field-label")
                yield Static(
                    self.result.snippet or "[dim]No snippet available[/dim]",
                    classes="field-value snippet-value"
                )

                # Tags Section
                yield Label("🏷️  Tags", classes="field-label")
                tags_text = self._format_tags(self.result.tags)
                yield Static(tags_text, classes="field-value")

                # Module/Source Section
                yield Label("🔌 Module Source", classes="field-label")
                yield Static(
                    self.result.source_engine or "[dim]Unknown[/dim]",
                    classes="field-value"
                )

                # Category Section
                yield Label("📊 Category", classes="field-label")
                yield Static(
                    self.category or "[dim]Unknown[/dim]",
                    classes="field-value"
                )

                # Query Section
                yield Label("🎯 Query", classes="field-label")
                yield Static(
                    self.query_description or "[dim]No query description[/dim]",
                    classes="field-value"
                )

                # Timestamp Section
                yield Label("⏰ Timestamps", classes="field-label")
                timestamp_text = self._format_timestamps()
                yield Static(timestamp_text, classes="field-value")

                # Scoring Metadata Section (placeholder)
                yield Label("📊 Scoring Metadata", classes="field-label")
                scoring_text = self._format_scoring()
                yield Static(scoring_text, classes="field-value")

            # Action Buttons
            with Horizontal(id="detail-actions"):
                yield Button("🤖 Summarize with AI", id="btn-summarize", variant="primary")
                yield Button("💾 Export...", id="btn-export", variant="default")
                yield Button("❌ Close", id="btn-close", variant="error")

    def _format_tags(self, tags: str) -> str:
        """Format tags for display.

        Args:
            tags: Comma-separated tag string

        Returns:
            Formatted tags with color coding
        """
        if not tags:
            return "[dim]No tags[/dim]"

        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        if not tag_list:
            return "[dim]No tags[/dim]"

        # Color-code common tags
        tag_colors = {
            "high-risk": "red",
            "sensitive": "red",
            "exposed": "yellow",
            "public": "cyan",
            "verified": "green",
            "archived": "dim",
        }

        formatted_tags = []
        for tag in tag_list:
            color = tag_colors.get(tag.lower(), "white")
            formatted_tags.append(f"[{color}]#{tag}[/{color}]")

        return " ".join(formatted_tags)

    def _format_timestamps(self) -> str:
        """Format timestamp information.

        Returns:
            Formatted timestamp string
        """
        lines = []

        if self.result.first_seen_at:
            lines.append(f"First seen: [cyan]{self.result.first_seen_at}[/cyan]")
        else:
            lines.append("First seen: [dim]Unknown[/dim]")

        if self.result.last_seen_at:
            lines.append(f"Last seen:  [cyan]{self.result.last_seen_at}[/cyan]")
        else:
            lines.append("Last seen:  [dim]Unknown[/dim]")

        return "\n".join(lines)

    def _format_scoring(self) -> str:
        """Format scoring metadata.

        Returns:
            Formatted scoring information
        """
        # Placeholder scoring logic - could be enhanced with actual scoring
        score_data = []

        # Calculate some basic metrics
        has_sensitive_keywords = any(
            keyword in (self.result.title + self.result.snippet).lower()
            for keyword in ["password", "secret", "api", "key", "token", "admin", "backup"]
        )

        if has_sensitive_keywords:
            score_data.append("[red]⚠️  Contains sensitive keywords[/red]")

        if self.result.tags and "high-risk" in self.result.tags.lower():
            score_data.append("[red]⚠️  High-risk tag applied[/red]")

        # Check URL for suspicious patterns
        suspicious_patterns = [".sql", ".bak", ".env", "/.git/", "/backup/", "/admin/"]
        if any(pattern in self.result.url.lower() for pattern in suspicious_patterns):
            score_data.append("[yellow]⚠️  Suspicious URL pattern detected[/yellow]")

        if not score_data:
            score_data.append("[green]✓ No immediate risk indicators[/green]")

        return "\n".join(score_data)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event
        """
        if event.button.id == "btn-summarize":
            await self.action_summarize()
        elif event.button.id == "btn-export":
            await self.action_export()
        elif event.button.id == "btn-close":
            self.dismiss()

    async def action_summarize(self) -> None:
        """Action: Summarize the result with AI."""
        # Import here to avoid circular imports
        from .reporting import Reporter
        from .config import config
        from .llm_client import get_llm_client

        # Log to event log if app has it
        if hasattr(self.app, 'log_event'):
            self.app.log_event("ai", f"Summarizing result: {self.result.url[:50]}...")

        try:
            # Create a minimal AI summary using the LLM client
            llm_client = get_llm_client(config.DEFAULT_LLM_PROVIDER)

            prompt = f"""Analyze this search result and provide a brief security assessment:

URL: {self.result.url}
Title: {self.result.title}
Snippet: {self.result.snippet}
Tags: {self.result.tags}

Provide:
1. What this result reveals
2. Potential security implications
3. Recommended actions (if any)

Keep it concise (3-4 sentences)."""

            summary = await llm_client.generate_async(
                system_prompt="You are a security analyst reviewing OSINT results.",
                user_prompt=prompt
            )

            # Update the snippet field with summary for now
            # In a real implementation, this would open another modal or panel
            if hasattr(self.app, 'log_event'):
                self.app.log_event("success", "AI summary generated")

            # Show summary in a simple way (could be enhanced with another modal)
            summary_widget = self.query_one("#detail-content", ScrollableContainer)
            summary_widget.mount(Label("\n🤖 AI Summary", classes="field-label"))
            summary_widget.mount(Static(summary, classes="field-value ai-summary"))

        except Exception as e:
            if hasattr(self.app, 'log_event'):
                self.app.log_event("error", f"Failed to generate summary: {str(e)}")

    async def action_export(self) -> None:
        """Action: Export the result with format selection."""
        from .export import get_exporter, ExportFormat
        from .project import ProjectManager

        if hasattr(self.app, 'log_event'):
            self.app.log_event("info", f"Exporting result: {self.result.url[:50]}...")

        try:
            # Get project manager
            pm = ProjectManager()

            # Get query object for full metadata
            query = None
            if hasattr(self.app, 'current_project') and self.app.current_project:
                queries = pm.list_queries(self.app.current_project.id)
                query = next((q for q in queries if q.id == self.result.query_id), None)

            # Export in all formats (user can choose which to use)
            formats = [
                (ExportFormat.JSON, "JSON"),
                (ExportFormat.MARKDOWN, "Markdown"),
                (ExportFormat.HTML, "HTML")
            ]

            exported_files = []
            for fmt, label in formats:
                try:
                    exporter = get_exporter(fmt, pm)
                    output_path = exporter.export_result(self.result, query, self.category)
                    exported_files.append((label, output_path.name))
                except Exception as e:
                    if hasattr(self.app, 'log_event'):
                        self.app.log_event("error", f"{label} export failed: {str(e)}")

            if exported_files:
                files_str = ", ".join([f"{label} ({name})" for label, name in exported_files])
                if hasattr(self.app, 'log_event'):
                    self.app.log_event("success", f"Exported to: {files_str}")
            else:
                if hasattr(self.app, 'log_event'):
                    self.app.log_event("error", "All exports failed")

        except Exception as e:
            if hasattr(self.app, 'log_event'):
                self.app.log_event("error", f"Export failed: {str(e)}")
