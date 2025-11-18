"""Terminal User Interface for osint85 using Textual."""

from typing import Optional, List
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, ListView, ListItem, Label, DataTable, Log,
    Button, Static, Input, Checkbox, ProgressBar
)
from textual.binding import Binding
from textual.screen import ModalScreen
from textual import events
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel

from .project import ProjectManager
from .dorks import DorkGenerator
from .scanner import Scanner
from .reporting import Reporter
from .database import Target, Query, Result
from .config import config


# Categories for the sidebar
CATEGORIES = [
    ("exposed_backups", "🗄️  Exposed Backups", "high"),
    ("config_files", "⚙️  Config Files", "high"),
    ("staging_environments", "🔧 Staging Environments", "medium"),
    ("login_portals", "🔐 Admin Panels", "low"),
    ("exposed_directories", "📁 Directory Listings", "medium"),
    ("debug_endpoints", "🐛 Debug Endpoints", "high"),
    ("api_endpoints", "🔌 API Endpoints", "medium"),
    ("sensitive_documents", "📄 Sensitive Documents", "medium"),
]


class CategoryItem(Static):
    """A category item for the sidebar."""

    def __init__(self, category_id: str, label: str, risk: str):
        super().__init__()
        self.category_id = category_id
        self.label_text = label
        self.risk = risk

    def render(self) -> str:
        risk_color = {
            "high": "red",
            "medium": "yellow",
            "low": "cyan"
        }.get(self.risk, "white")
        return f"[{risk_color}]{self.label_text}[/{risk_color}]"


class Sidebar(ScrollableContainer):
    """Left category list with scrollable items."""

    selected_index: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Label("📊 RECON CATEGORIES", classes="sidebar-title")
        for cat_id, label, risk in CATEGORIES:
            yield CategoryItem(cat_id, label, risk)

    def on_mount(self):
        """Highlight first item on mount."""
        items = list(self.query(CategoryItem))
        if items:
            items[0].add_class("selected")

    def on_click(self, event: events.Click):
        """Handle category selection."""
        if isinstance(event.widget, CategoryItem):
            # Remove previous selection
            for item in self.query(CategoryItem):
                item.remove_class("selected")

            # Select new item
            event.widget.add_class("selected")

            # Notify app
            self.post_message(CategorySelected(event.widget.category_id, event.widget.label_text))


class CategorySelected(events.Message):
    """Message sent when a category is selected."""

    def __init__(self, category_id: str, label: str):
        super().__init__()
        self.category_id = category_id
        self.label = label


class QueryBuilderPanel(Container):
    """Top-right panel that shows dork sets and query details."""

    current_category: reactive[str] = reactive("none")
    query_count: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Static("🎯 QUERY BUILDER", classes="panel-title")
        yield Label("Select a category to generate OSINT queries.", id="qb-desc")
        yield Container(id="query-list")
        yield Horizontal(
            Button("🚀 Generate Queries", id="btn-generate", variant="primary"),
            Button("▶️  Run Scan", id="btn-scan", variant="success"),
            classes="button-row"
        )

    def update_category(self, category_id: str, label: str):
        """Update the panel for a new category."""
        self.current_category = category_id
        desc = self.query_one("#qb-desc", Label)
        desc.update(f"Category: [cyan]{label}[/cyan]")

        # Display existing queries for this category
        self.refresh_queries()

    def refresh_queries(self):
        """Refresh the query list from database."""
        container = self.query_one("#query-list", Container)
        container.remove_children()

        # Get current project from app
        app = self.app
        if hasattr(app, 'current_project') and app.current_project:
            pm = ProjectManager()
            queries = pm.list_queries(app.current_project.id)

            # Filter by current category
            category_queries = [q for q in queries if q.category == self.current_category]
            self.query_count = len(category_queries)

            if category_queries:
                for q in category_queries[:5]:  # Show first 5
                    enabled = "✓" if q.enabled else "✗"
                    risk_color = {"high": "red", "medium": "yellow", "low": "cyan"}.get(q.risk_level, "white")
                    query_widget = Label(
                        f"[{risk_color}]{enabled}[/{risk_color}] {q.description[:50]}..."
                    )
                    container.mount(query_widget)

                if len(category_queries) > 5:
                    container.mount(Label(f"[dim]... and {len(category_queries) - 5} more[/dim]"))
            else:
                container.mount(Label("[dim]No queries for this category yet[/dim]"))


class ResultGrid(DataTable):
    """Bottom-right results table."""

    def on_mount(self):
        self.add_columns("🔗 URL", "📋 Title", "🏷️  Tags")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def load_results(self, category_id: str):
        """Load results for a specific category."""
        self.clear()

        app = self.app
        if hasattr(app, 'current_project') and app.current_project:
            pm = ProjectManager()
            queries = pm.list_queries(app.current_project.id)

            # Get query IDs for this category
            category_query_ids = [q.id for q in queries if q.category == category_id]

            # Get results for these queries
            results = []
            for qid in category_query_ids:
                results.extend(pm.get_results_by_query(qid))

            # Add to table
            for r in results[:50]:  # Limit to 50
                url_short = r.url[:50] + "..." if len(r.url) > 50 else r.url
                title_short = r.title[:40] + "..." if len(r.title) > 40 else r.title
                self.add_row(url_short, title_short, r.tags or "-")


class EventLog(Log):
    """Event log with custom styling."""

    def write_event(self, event_type: str, message: str):
        """Write a formatted event to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icons = {
            "info": "ℹ️",
            "success": "✓",
            "error": "✗",
            "scan": "🔍",
            "ai": "🤖",
        }
        icon = icons.get(event_type, "▶")
        color = {
            "info": "cyan",
            "success": "green",
            "error": "red",
            "scan": "yellow",
            "ai": "magenta"
        }.get(event_type, "white")

        self.write(f"[dim]{timestamp}[/dim] [{color}]{icon} {message}[/{color}]")


class ProjectSelectScreen(ModalScreen):
    """Modal screen for selecting/creating a project."""

    BINDINGS = [("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Container(id="project-modal"):
            yield Static("🎯 SELECT PROJECT", classes="modal-title")
            yield ListView(id="project-list")
            yield Horizontal(
                Button("New Project", id="btn-new-project", variant="primary"),
                Button("Cancel", id="btn-cancel"),
                classes="button-row"
            )

    def on_mount(self):
        """Load projects on mount."""
        pm = ProjectManager()
        projects = pm.list_projects()

        project_list = self.query_one("#project-list", ListView)
        for project in projects:
            project_list.append(
                ListItem(Label(f"{project.name} - {project.primary_domain}"), id=str(project.id))
            )

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle project selection."""
        project_id = int(event.item.id)
        self.dismiss(project_id)

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-new-project":
            # TODO: Show new project form
            self.dismiss(None)


class GenerateQueriesScreen(ModalScreen):
    """Modal screen for generating queries."""

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, category_id: str, category_label: str):
        super().__init__()
        self.category_id = category_id
        self.category_label = category_label

    def compose(self) -> ComposeResult:
        with Container(id="generate-modal"):
            yield Static(f"🤖 GENERATE QUERIES - {self.category_label}", classes="modal-title")
            yield Label("Enter reconnaissance goal:")
            yield Input(placeholder="e.g., Find exposed backup files", id="goal-input")
            yield Horizontal(
                Button("Generate", id="btn-generate", variant="primary"),
                Button("Cancel", id="btn-cancel"),
                classes="button-row"
            )
            yield Container(id="generation-status")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-generate":
            goal_input = self.query_one("#goal-input", Input)
            goal = goal_input.value

            if goal:
                self.generate_queries(goal)

    def generate_queries(self, goal: str):
        """Generate queries using LLM."""
        status = self.query_one("#generation-status", Container)
        status.mount(Label("[yellow]🤖 Generating queries with AI...[/yellow]"))

        try:
            # Get current project
            app = self.app
            if not hasattr(app, 'current_project') or not app.current_project:
                status.mount(Label("[red]No project selected[/red]"))
                return

            # Generate queries
            generator = DorkGenerator()
            queries = generator.generate(app.current_project, goal)

            # Filter by category if needed
            category_queries = [q for q in queries if q['category'] == self.category_id]

            if not category_queries:
                # If no queries for this category, use all
                category_queries = queries

            # Save to database
            pm = ProjectManager()
            pm.save_queries(app.current_project.id, category_queries)

            status.mount(Label(f"[green]✓ Generated {len(category_queries)} queries[/green]"))

            # Wait a moment then dismiss
            self.set_timer(1.5, lambda: self.dismiss(len(category_queries)))

        except Exception as e:
            status.mount(Label(f"[red]✗ Error: {e}[/red]"))


class ScanProgressScreen(ModalScreen):
    """Modal screen showing scan progress."""

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, category_id: str):
        super().__init__()
        self.category_id = category_id

    def compose(self) -> ComposeResult:
        with Container(id="scan-modal"):
            yield Static("🔍 SCANNING...", classes="modal-title")
            yield ProgressBar(id="scan-progress")
            yield Label("Initializing scan...", id="scan-status")
            yield Button("Stop", id="btn-stop", variant="error")

    def on_mount(self):
        """Start scan on mount."""
        self.run_scan()

    def run_scan(self):
        """Run the scan."""
        status_label = self.query_one("#scan-status", Label)

        try:
            app = self.app
            if not hasattr(app, 'current_project') or not app.current_project:
                status_label.update("[red]No project selected[/red]")
                return

            pm = ProjectManager()
            queries = pm.get_enabled_queries(app.current_project.id)

            # Filter by category
            category_queries = [q for q in queries if q.category == self.category_id]

            if not category_queries:
                status_label.update(f"[yellow]No enabled queries for this category[/yellow]")
                self.set_timer(2, lambda: self.dismiss(0))
                return

            status_label.update(f"[cyan]Running {len(category_queries)} queries...[/cyan]")

            # Run scanner
            scanner = Scanner(pm, mock=True)  # Use mock for demo
            scanner.run(app.current_project, category_queries, max_results=20, delay=0.5)

            status_label.update(f"[green]✓ Scan complete![/green]")
            self.set_timer(1.5, lambda: self.dismiss(len(category_queries)))

        except Exception as e:
            status_label.update(f"[red]✗ Error: {e}[/red]")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle stop button."""
        if event.button.id == "btn-stop":
            self.dismiss(0)


class OSINTApp(App):
    """OSINT-85 Command Nexus TUI Application."""

    CSS_PATH = "osint85.tcss"
    TITLE = "OSINT-85 Command Nexus"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("slash", "command_palette", "Commands", show=True),
        Binding("p", "select_project", "Project", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    current_project: reactive[Optional[Target]] = reactive(None)
    current_category: reactive[str] = reactive("exposed_backups")

    def __init__(self):
        super().__init__()
        config.ensure_directories()

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()

        yield Horizontal(
            Sidebar(id="sidebar"),
            Vertical(
                QueryBuilderPanel(id="query-builder"),
                ResultGrid(id="results"),
                id="content-stack",
            ),
            id="main-layout"
        )

        yield EventLog(id="event-log", highlight=True)
        yield Footer()

    def on_mount(self):
        """Initialize the app on mount."""
        log = self.query_one("#event-log", EventLog)
        log.write_event("info", "OSINT-85 Command Nexus initialized")
        log.write_event("info", "Press 'p' to select a project")

        # Try to load last project or prompt selection
        self.action_select_project()

    def on_category_selected(self, message: CategorySelected):
        """Handle category selection."""
        self.current_category = message.category_id

        log = self.query_one("#event-log", EventLog)
        log.write_event("info", f"Category selected: {message.label}")

        # Update query builder
        qb = self.query_one("#query-builder", QueryBuilderPanel)
        qb.update_category(message.category_id, message.label)

        # Update results grid
        results = self.query_one("#results", ResultGrid)
        results.load_results(message.category_id)

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        log = self.query_one("#event-log", EventLog)

        if event.button.id == "btn-generate":
            if not self.current_project:
                log.write_event("error", "No project selected")
                return

            # Get current category label
            category_label = next(
                (label for cat_id, label, _ in CATEGORIES if cat_id == self.current_category),
                "Unknown"
            )

            # Show generate queries modal
            self.push_screen(
                GenerateQueriesScreen(self.current_category, category_label),
                self.on_queries_generated
            )

        elif event.button.id == "btn-scan":
            if not self.current_project:
                log.write_event("error", "No project selected")
                return

            # Show scan progress modal
            self.push_screen(
                ScanProgressScreen(self.current_category),
                self.on_scan_complete
            )

    def on_queries_generated(self, count: Optional[int]):
        """Handle query generation completion."""
        if count:
            log = self.query_one("#event-log", EventLog)
            log.write_event("success", f"Generated {count} queries")

            # Refresh query builder
            qb = self.query_one("#query-builder", QueryBuilderPanel)
            qb.refresh_queries()

    def on_scan_complete(self, count: Optional[int]):
        """Handle scan completion."""
        if count:
            log = self.query_one("#event-log", EventLog)
            log.write_event("success", f"Scan complete - processed {count} queries")

            # Refresh results
            results = self.query_one("#results", ResultGrid)
            results.load_results(self.current_category)

    def action_select_project(self):
        """Show project selection screen."""
        self.push_screen(ProjectSelectScreen(), self.on_project_selected)

    def on_project_selected(self, project_id: Optional[int]):
        """Handle project selection."""
        if project_id:
            pm = ProjectManager()
            self.current_project = pm.get_project(project_id)

            log = self.query_one("#event-log", EventLog)
            log.write_event("success", f"Project loaded: {self.current_project.name}")

            # Update title
            self.sub_title = f"Project: {self.current_project.name.upper()}"

            # Refresh query builder and results
            qb = self.query_one("#query-builder", QueryBuilderPanel)
            qb.refresh_queries()

            results = self.query_one("#results", ResultGrid)
            results.load_results(self.current_category)

    def action_refresh(self):
        """Refresh all data."""
        log = self.query_one("#event-log", EventLog)
        log.write_event("info", "Refreshing data...")

        qb = self.query_one("#query-builder", QueryBuilderPanel)
        qb.refresh_queries()

        results = self.query_one("#results", ResultGrid)
        results.load_results(self.current_category)

        log.write_event("success", "Data refreshed")


def run_tui():
    """Run the TUI application."""
    app = OSINTApp()
    app.run()


if __name__ == "__main__":
    run_tui()
