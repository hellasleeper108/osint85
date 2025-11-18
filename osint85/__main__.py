"""CLI interface for osint85."""

import sys
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from .project import ProjectManager
from .dorks import DorkGenerator
from .scanner import Scanner
from .reporting import Reporter
from .config import config

app = typer.Typer(
    name="osint85",
    help="Terminal-based OSINT assistant with LLM-powered dork generation",
    add_completion=False
)

console = Console()

# Global state for current project
_current_project_id: Optional[int] = None


def _get_project_manager() -> ProjectManager:
    """Get project manager instance."""
    return ProjectManager()


def _ensure_project(project_id: Optional[int] = None) -> int:
    """Ensure a project is selected.

    Args:
        project_id: Explicit project ID (optional)

    Returns:
        Project ID

    Raises:
        typer.Exit: If no project is selected
    """
    global _current_project_id

    if project_id is not None:
        return project_id

    if _current_project_id is not None:
        return _current_project_id

    console.print("[red]No project selected. Use 'osint85 init' to create a project.[/red]")
    raise typer.Exit(1)


@app.callback()
def main_callback():
    """osint85 - Terminal-based OSINT assistant."""
    # Display disclaimer on first run
    pass


@app.command()
def disclaimer():
    """Display legal and ethical usage disclaimer."""
    disclaimer_text = """
[bold red]LEGAL AND ETHICAL USAGE DISCLAIMER[/bold red]

osint85 is a tool for authorized security reconnaissance only.

[bold yellow]YOU MUST ONLY USE THIS TOOL:[/bold yellow]
✓ On assets you own or control
✓ With explicit written permission from the asset owner
✓ Within the scope of authorized bug bounty programs
✓ In controlled lab/training environments

[bold red]PROHIBITED USES:[/bold red]
✗ Unauthorized reconnaissance or scanning
✗ Testing systems without permission
✗ Violation of terms of service
✗ Any malicious or illegal activities

[bold cyan]LEGAL RESPONSIBILITY:[/bold cyan]
You are solely responsible for ensuring your use of this tool
complies with all applicable laws and regulations. The authors
and contributors assume no liability for misuse.

[bold green]BEST PRACTICES:[/bold green]
• Always obtain written authorization before testing
• Respect rate limits and terms of service
• Document your authorization and scope
• Use findings for defensive purposes only
• Report vulnerabilities responsibly

By using osint85, you agree to use it responsibly and legally.
"""
    rprint(Panel(disclaimer_text, title="osint85 Disclaimer", border_style="red"))


@app.command()
def init(
    name: str = typer.Option(..., "--name", "-n", help="Project name"),
    domain: str = typer.Option(..., "--domain", "-d", help="Primary domain to investigate"),
    notes: str = typer.Option("", "--notes", help="Additional notes"),
    scope: str = typer.Option("", "--scope", help="Authorized scope definition")
):
    """Create a new OSINT project."""
    global _current_project_id

    # Validate config
    if not config.validate():
        console.print("[red]Configuration validation failed. Please check your .env file.[/red]")
        raise typer.Exit(1)

    # Ensure directories exist
    config.ensure_directories()

    pm = _get_project_manager()
    project = pm.create_project(name=name, domain=domain, notes=notes, scope=scope)

    _current_project_id = project.id

    console.print(f"[green]✓[/green] Created project: {project.name} (ID: {project.id})")
    console.print(f"  Domain: {project.primary_domain}")
    if scope:
        console.print(f"  Scope: {scope}")


@app.command()
def projects():
    """List all projects."""
    pm = _get_project_manager()
    all_projects = pm.list_projects()

    if not all_projects:
        console.print("[yellow]No projects found. Use 'osint85 init' to create one.[/yellow]")
        return

    table = Table(title="OSINT Projects")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Domain", style="blue")
    table.add_column("Created", style="magenta")

    for project in all_projects:
        table.add_row(
            str(project.id),
            project.name,
            project.primary_domain,
            project.created_at[:10] if project.created_at else "N/A"
        )

    console.print(table)


@app.command()
def dorks_generate(
    goal: str = typer.Option(..., "--goal", "-g", help="Reconnaissance goal"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Project ID"),
    mock_llm: bool = typer.Option(False, "--mock", help="Use mock LLM for testing")
):
    """Generate dork queries using LLM."""
    pid = _ensure_project(project_id)

    pm = _get_project_manager()
    project = pm.get_project(pid)

    console.print(f"[cyan]Generating dork queries for: {project.name}[/cyan]")
    console.print(f"Goal: {goal}")

    try:
        generator = DorkGenerator()
        queries = generator.generate(project, goal)

        console.print(f"\n[green]✓[/green] Generated {len(queries)} queries")

        # Save queries
        saved_queries = pm.save_queries(pid, queries)

        # Display queries
        table = Table(title="Generated Queries")
        table.add_column("ID", style="cyan")
        table.add_column("Category", style="yellow")
        table.add_column("Risk", style="red")
        table.add_column("Description", style="green")

        for q in saved_queries:
            table.add_row(str(q.id), q.category, q.risk_level, q.description)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error generating queries: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def dorks_list(
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Project ID")
):
    """List all dork queries for a project."""
    pid = _ensure_project(project_id)

    pm = _get_project_manager()
    queries = pm.list_queries(pid)

    if not queries:
        console.print("[yellow]No queries found. Use 'osint85 dorks-generate' to create some.[/yellow]")
        return

    table = Table(title="Dork Queries")
    table.add_column("ID", style="cyan")
    table.add_column("Enabled", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Risk", style="red")
    table.add_column("Query", style="blue")

    for q in queries:
        enabled_symbol = "✓" if q.enabled else "✗"
        table.add_row(
            str(q.id),
            enabled_symbol,
            q.category,
            q.risk_level,
            q.query[:60] + "..." if len(q.query) > 60 else q.query
        )

    console.print(table)


@app.command()
def dorks_toggle(
    query_ids: str = typer.Argument(..., help="Comma-separated query IDs to toggle"),
    enable: bool = typer.Option(None, "--enable/--disable", help="Enable or disable")
):
    """Enable or disable specific dork queries."""
    pm = _get_project_manager()

    ids = [int(x.strip()) for x in query_ids.split(",")]

    for qid in ids:
        try:
            pm.toggle_query(qid, enable)
            action = "enabled" if enable else "disabled"
            console.print(f"[green]✓[/green] Query {qid} {action}")
        except Exception as e:
            console.print(f"[red]Error toggling query {qid}: {e}[/red]")


@app.command()
def scan(
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Project ID"),
    max_results: int = typer.Option(20, "--max-results", "-m", help="Max results per query"),
    delay: float = typer.Option(1.0, "--delay", "-d", help="Delay between queries (seconds)"),
    mock: bool = typer.Option(False, "--mock", help="Use mock search for testing")
):
    """Run enabled dork queries and collect results."""
    pid = _ensure_project(project_id)

    pm = _get_project_manager()
    project = pm.get_project(pid)
    queries = pm.get_enabled_queries(pid)

    if not queries:
        console.print("[yellow]No enabled queries. Use 'osint85 dorks-generate' first.[/yellow]")
        return

    console.print(f"[cyan]Starting scan for: {project.name}[/cyan]")
    console.print(f"Queries: {len(queries)}")
    console.print(f"Max results per query: {max_results}")

    if mock:
        console.print("[yellow]Using mock search client for testing[/yellow]")

    try:
        scanner = Scanner(pm, mock=mock)
        scanner.run(project, queries, max_results=max_results, delay=delay)
        console.print("\n[green]✓[/green] Scan complete")

    except Exception as e:
        console.print(f"\n[red]Scan error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def results_list(
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Project ID"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    limit: int = typer.Option(50, "--limit", "-l", help="Limit results displayed")
):
    """List search results for a project."""
    pid = _ensure_project(project_id)

    pm = _get_project_manager()
    results = pm.get_all_results(pid)

    if not results:
        console.print("[yellow]No results found. Use 'osint85 scan' to collect results.[/yellow]")
        return

    # Filter by category if specified
    if category:
        queries = pm.list_queries(pid)
        category_query_ids = [q.id for q in queries if q.category == category]
        results = [r for r in results if r.query_id in category_query_ids]

    table = Table(title=f"Search Results ({len(results)} total)")
    table.add_column("ID", style="cyan")
    table.add_column("URL", style="blue", no_wrap=False)
    table.add_column("Tags", style="yellow")
    table.add_column("Seen", style="magenta")

    for r in results[:limit]:
        table.add_row(
            str(r.id),
            r.url[:80] + "..." if len(r.url) > 80 else r.url,
            r.tags or "-",
            r.first_seen_at[:10] if r.first_seen_at else "N/A"
        )

    console.print(table)

    if len(results) > limit:
        console.print(f"\n[yellow]Showing {limit} of {len(results)} results. Use --limit to see more.[/yellow]")


@app.command()
def report(
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Project ID"),
    output: str = typer.Option("report.md", "--out", "-o", help="Output file path"),
    summary_only: bool = typer.Option(False, "--summary", "-s", help="Show summary only")
):
    """Generate a comprehensive report."""
    pid = _ensure_project(project_id)

    pm = _get_project_manager()
    project = pm.get_project(pid)
    reporter = Reporter(pm)

    if summary_only:
        console.print(reporter.generate_summary(project))
    else:
        console.print(f"[cyan]Generating report for: {project.name}[/cyan]")
        try:
            reporter.generate(project, out_path=output)
            console.print(f"[green]✓[/green] Report generated: {output}")
        except Exception as e:
            console.print(f"[red]Error generating report: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def tui():
    """Launch the interactive TUI (Terminal User Interface)."""
    console.print("[cyan]Launching OSINT-85 Command Nexus...[/cyan]\n")

    try:
        from .tui import run_tui
        run_tui()
    except ImportError as e:
        console.print(f"[red]Error: TUI dependencies not installed.[/red]")
        console.print(f"[yellow]Install with: pip install 'textual>=0.47.1'[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]TUI error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    from . import __version__
    console.print(f"osint85 version {__version__}")


if __name__ == "__main__":
    # Show disclaimer on first run
    if len(sys.argv) == 1:
        disclaimer()
        console.print("\n[cyan]Run 'osint85 --help' to see available commands.[/cyan]\n")
    else:
        app()
