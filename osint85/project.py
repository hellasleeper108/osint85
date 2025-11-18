"""Project and target management for osint85."""

from typing import Optional, List
from pathlib import Path

from .database import Database, Target, Query, Result
from .config import config


class ProjectManager:
    """Manages OSINT projects and targets."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize project manager.

        Args:
            db_path: Path to SQLite database (defaults to config)
        """
        self.db_path = db_path or config.DATABASE_PATH
        self.db = Database(self.db_path)

    def create_project(self, name: str, domain: str, notes: str = "", scope: str = "") -> Target:
        """Create a new project/target.

        Args:
            name: Project name
            domain: Primary domain to investigate
            notes: Additional notes
            scope: Authorized scope definition

        Returns:
            Created Target object
        """
        return self.db.create_target(
            name=name,
            primary_domain=domain,
            notes=notes,
            scope=scope
        )

    def get_project(self, project_id: int) -> Target:
        """Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            Target object
        """
        return self.db.get_target(project_id)

    def list_projects(self) -> List[Target]:
        """List all projects.

        Returns:
            List of Target objects
        """
        return self.db.list_targets()

    def save_queries(self, project_id: int, queries: List[dict]) -> List[Query]:
        """Save queries for a project.

        Args:
            project_id: Project ID
            queries: List of query dictionaries

        Returns:
            List of created Query objects
        """
        return self.db.save_queries(project_id, queries)

    def get_enabled_queries(self, project_id: int) -> List[Query]:
        """Get enabled queries for a project.

        Args:
            project_id: Project ID

        Returns:
            List of enabled Query objects
        """
        return self.db.get_enabled_queries(project_id)

    def list_queries(self, project_id: int) -> List[Query]:
        """List all queries for a project.

        Args:
            project_id: Project ID

        Returns:
            List of Query objects
        """
        return self.db.list_queries(project_id)

    def toggle_query(self, query_id: int, enabled: bool):
        """Enable or disable a query.

        Args:
            query_id: Query ID
            enabled: True to enable, False to disable
        """
        self.db.toggle_query(query_id, enabled)

    def save_result(self, query_id: int, url: str, title: str = "",
                   snippet: str = "", source_engine: str = "", tags: str = "") -> Result:
        """Save a search result.

        Args:
            query_id: Query ID
            url: Result URL
            title: Page title
            snippet: Search snippet
            source_engine: Search engine name
            tags: Comma-separated tags

        Returns:
            Created or updated Result object
        """
        return self.db.save_result(
            query_id=query_id,
            url=url,
            title=title,
            snippet=snippet,
            source_engine=source_engine,
            tags=tags
        )

    def get_results_by_query(self, query_id: int) -> List[Result]:
        """Get all results for a query.

        Args:
            query_id: Query ID

        Returns:
            List of Result objects
        """
        return self.db.get_results_by_query(query_id)

    def get_all_results(self, project_id: int) -> List[Result]:
        """Get all results for a project.

        Args:
            project_id: Project ID

        Returns:
            List of Result objects
        """
        return self.db.get_all_results(project_id)

    def close(self):
        """Close database connection."""
        self.db.close()
