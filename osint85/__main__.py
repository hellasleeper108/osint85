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
from .export import get_exporter, ExportFormat
from .dedupe import DeduplicationEngine

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
def export_result(
    result_id: int = typer.Argument(..., help="Result ID to export"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (markdown, json, html)"),
    output: Optional[str] = typer.Option(None, "--out", "-o", help="Output file path (auto-generated if not specified)")
):
    """Export a single result to file."""
    pm = _get_project_manager()

    # Get the result
    try:
        # Find result by ID across all projects
        all_results = []
        for project in pm.list_projects():
            all_results.extend(pm.get_all_results(project.id))

        result = next((r for r in all_results if r.id == result_id), None)

        if not result:
            console.print(f"[red]Result with ID {result_id} not found.[/red]")
            raise typer.Exit(1)

        # Get associated query
        queries = []
        for project in pm.list_projects():
            queries.extend(pm.list_queries(project.id))

        query = next((q for q in queries if q.id == result.query_id), None)
        category = query.category if query else ""

        # Export
        exporter = get_exporter(format.lower(), pm)

        if output:
            # Use custom output path
            from pathlib import Path
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() == ExportFormat.MARKDOWN:
                content = exporter._generate_result_markdown(result, query, category)
            elif format.lower() == ExportFormat.JSON:
                import json
                from datetime import datetime
                content = json.dumps({
                    "schema_version": exporter.pm.__class__.__name__,
                    "export_type": "single_result",
                    "exported_at": datetime.now().isoformat(),
                    "result": exporter._result_to_dict(result),
                    "query": exporter._query_to_dict(query) if query else None,
                    "category": category
                }, indent=2)
            elif format.lower() == ExportFormat.HTML:
                content = exporter._generate_result_html(result, query, category)
                from datetime import datetime
                content = exporter.HTML_TEMPLATE.format(
                    title=f"OSINT-85 Result: {result.title or result.url[:50]}",
                    content=content,
                    version="1.0.0",
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                console.print(f"[red]Unsupported format: {format}[/red]")
                raise typer.Exit(1)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            console.print(f"[green]✓[/green] Exported result {result_id} to: {output_path}")
        else:
            # Use auto-generated path
            output_path = exporter.export_result(result, query, category)
            console.print(f"[green]✓[/green] Exported result {result_id} to: {output_path}")

    except Exception as e:
        console.print(f"[red]Export error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def export_category(
    category: str = typer.Argument(..., help="Category name to export"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (markdown, json, html)"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Project ID"),
    output: Optional[str] = typer.Option(None, "--out", "-o", help="Output file path")
):
    """Export all results for a category."""
    pid = _ensure_project(project_id)

    pm = _get_project_manager()
    project = pm.get_project(pid)

    try:
        exporter = get_exporter(format.lower(), pm)

        if output:
            # Use custom output path
            from pathlib import Path
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Get all queries and results for category
            queries = pm.list_queries(pid)
            category_queries = [q for q in queries if q.category == category]

            all_results = []
            for query in category_queries:
                results = pm.get_results_by_query(query.id)
                all_results.extend([(query, r) for r in results])

            if not all_results:
                console.print(f"[yellow]No results found for category: {category}[/yellow]")
                return

            # Generate content
            if format.lower() == ExportFormat.MARKDOWN:
                content = exporter._generate_category_markdown(project, category, all_results)
            elif format.lower() == ExportFormat.JSON:
                import json
                from datetime import datetime
                results_data = []
                for query, result in all_results:
                    results_data.append({
                        "result": exporter._result_to_dict(result),
                        "query": exporter._query_to_dict(query)
                    })
                content = json.dumps({
                    "schema_version": "1.0.0",
                    "export_type": "category",
                    "exported_at": datetime.now().isoformat(),
                    "target": exporter._target_to_dict(project),
                    "category": category,
                    "total_results": len(results_data),
                    "results": results_data
                }, indent=2)
            elif format.lower() == ExportFormat.HTML:
                content = exporter._generate_category_html(project, category, all_results)
                from datetime import datetime
                content = exporter.HTML_TEMPLATE.format(
                    title=f"OSINT-85 Category Report: {category}",
                    content=content,
                    version="1.0.0",
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                console.print(f"[red]Unsupported format: {format}[/red]")
                raise typer.Exit(1)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            console.print(f"[green]✓[/green] Exported {len(all_results)} results to: {output_path}")
        else:
            # Use auto-generated path
            output_path = exporter.export_category(project, category)

            # Count results
            queries = pm.list_queries(pid)
            category_queries = [q for q in queries if q.category == category]
            total_results = sum(len(pm.get_results_by_query(q.id)) for q in category_queries)

            console.print(f"[green]✓[/green] Exported {total_results} results to: {output_path}")

    except Exception as e:
        console.print(f"[red]Export error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def export_project(
    format: str = typer.Option("json", "--format", "-f", help="Export format (markdown, json, html)"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Project ID"),
    output: Optional[str] = typer.Option(None, "--out", "-o", help="Output file path")
):
    """Export entire project to file."""
    pid = _ensure_project(project_id)

    pm = _get_project_manager()
    project = pm.get_project(pid)

    console.print(f"[cyan]Exporting project: {project.name}[/cyan]")

    try:
        exporter = get_exporter(format.lower(), pm)

        if output:
            # Use custom output path
            from pathlib import Path
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Get all data
            queries = pm.list_queries(pid)
            categories = {}

            for query in queries:
                if query.category not in categories:
                    categories[query.category] = []
                results = pm.get_results_by_query(query.id)
                categories[query.category].extend([(query, r) for r in results])

            total_results = sum(len(results) for results in categories.values())

            if total_results == 0:
                console.print(f"[yellow]No results found in project. Run 'osint85 scan' first.[/yellow]")
                return

            # Generate content
            if format.lower() == ExportFormat.MARKDOWN:
                content = exporter._generate_project_markdown(project, categories)
            elif format.lower() == ExportFormat.JSON:
                import json
                from datetime import datetime
                json_categories = {}
                for category, results in categories.items():
                    json_categories[category] = []
                    for query, result in results:
                        json_categories[category].append({
                            "result": exporter._result_to_dict(result),
                            "query": exporter._query_to_dict(query)
                        })
                content = json.dumps({
                    "schema_version": "1.0.0",
                    "export_type": "full_project",
                    "exported_at": datetime.now().isoformat(),
                    "target": exporter._target_to_dict(project),
                    "total_results": total_results,
                    "total_categories": len(categories),
                    "categories": json_categories
                }, indent=2)
            elif format.lower() == ExportFormat.HTML:
                content = exporter._generate_project_html(project, categories)
                from datetime import datetime
                content = exporter.HTML_TEMPLATE.format(
                    title=f"OSINT-85 Full Report: {project.name}",
                    content=content,
                    version="1.0.0",
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                console.print(f"[red]Unsupported format: {format}[/red]")
                raise typer.Exit(1)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            console.print(f"[green]✓[/green] Exported {total_results} results across {len(categories)} categories to: {output_path}")
        else:
            # Use auto-generated path
            output_path = exporter.export_project(project)

            # Count results
            total_results = len(pm.get_all_results(pid))
            console.print(f"[green]✓[/green] Exported {total_results} results to: {output_path}")

    except Exception as e:
        console.print(f"[red]Export error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def dedupe_run(
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Project ID"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Specific category to deduplicate"),
    remove: bool = typer.Option(False, "--remove", "-r", help="Remove duplicates (not just mark)"),
    threshold: float = typer.Option(90.0, "--threshold", "-t", help="Fuzzy similarity threshold (0-100)")
):
    """Detect and mark/remove duplicate results."""
    pid = _ensure_project(project_id)

    pm = _get_project_manager()
    project = pm.get_project(pid)

    console.print(f"[cyan]Running deduplication for: {project.name}[/cyan]")
    if category:
        console.print(f"Category: {category}")
    console.print(f"Threshold: {threshold}%")

    try:
        engine = DeduplicationEngine(pm, fuzzy_threshold=threshold)

        # Get stats before
        before_stats = engine.get_duplicate_stats(pid)
        console.print(f"\n[yellow]Before deduplication:[/yellow]")
        console.print(f"  Total results: {before_stats['total_results']}")
        console.print(f"  Unique results: {before_stats['unique_results']}")
        console.print(f"  Duplicate results: {before_stats['duplicate_results']}")

        if remove:
            # Remove duplicates
            console.print(f"\n[cyan]Removing duplicates...[/cyan]")
            removed_count = engine.remove_duplicates(pid, category)
            console.print(f"[green]✓[/green] Removed {removed_count} duplicate results")
        else:
            # Just mark duplicates
            console.print(f"\n[cyan]Marking duplicates...[/cyan]")
            marked_count = engine.mark_duplicates(pid, category)
            console.print(f"[green]✓[/green] Marked {marked_count} results as duplicates")

        # Get stats after
        after_stats = engine.get_duplicate_stats(pid)
        console.print(f"\n[yellow]After deduplication:[/yellow]")
        console.print(f"  Total results: {after_stats['total_results']}")
        console.print(f"  Unique results: {after_stats['unique_results']}")
        console.print(f"  Duplicate results: {after_stats['duplicate_results']}")

        if not remove:
            console.print(f"\n[dim]Use --remove to delete duplicates instead of just marking them.[/dim]")

    except Exception as e:
        console.print(f"[red]Deduplication error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def dedupe_stats(
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Project ID")
):
    """Show duplicate statistics for a project."""
    pid = _ensure_project(project_id)

    pm = _get_project_manager()
    project = pm.get_project(pid)

    console.print(f"[cyan]Duplicate statistics for: {project.name}[/cyan]\n")

    try:
        engine = DeduplicationEngine(pm)
        stats = engine.get_duplicate_stats(pid)

        table = Table(title="Deduplication Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Results", str(stats['total_results']))
        table.add_row("Unique Results", str(stats['unique_results']))
        table.add_row("Duplicate Results", str(stats['duplicate_results']))
        table.add_row("Duplicate Groups", str(stats['duplicate_groups']))

        if stats['total_results'] > 0:
            dup_percent = (stats['duplicate_results'] / stats['total_results']) * 100
            table.add_row("Duplication Rate", f"{dup_percent:.1f}%")

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error getting stats: {e}[/red]")
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
