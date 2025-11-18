"""Export system for OSINT-85 results in multiple formats."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import asdict

from .database import Result, Query, Target
from .project import ProjectManager


# Export schema version for interoperability
EXPORT_SCHEMA_VERSION = "1.0.0"


class ExportFormat:
    """Export format constants."""
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


class Exporter:
    """Base exporter class."""

    def __init__(self, project_manager: Optional[ProjectManager] = None):
        """Initialize exporter.

        Args:
            project_manager: ProjectManager instance (optional)
        """
        self.pm = project_manager or ProjectManager()
        self.export_dir = Path(".osint85/exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, name: str, max_length: int = 50) -> str:
        """Sanitize a string for use as filename.

        Args:
            name: Input string
            max_length: Maximum filename length

        Returns:
            Sanitized filename string
        """
        # Remove/replace invalid characters
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return safe[:max_length]

    def _get_export_path(self, base_name: str, extension: str) -> Path:
        """Generate unique export path.

        Args:
            base_name: Base filename
            extension: File extension (without dot)

        Returns:
            Path object for export file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self._sanitize_filename(base_name)
        filename = f"{safe_name}_{timestamp}.{extension}"
        return self.export_dir / filename


class MarkdownExporter(Exporter):
    """Export results to Markdown format."""

    def export_result(self, result: Result, query: Optional[Query] = None,
                     category: str = "") -> Path:
        """Export a single result to Markdown.

        Args:
            result: Result object to export
            query: Associated Query object (optional)
            category: Category name (optional)

        Returns:
            Path to exported file
        """
        output_path = self._get_export_path(
            result.title or "result",
            "md"
        )

        content = self._generate_result_markdown(result, query, category)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path

    def export_category(self, target: Target, category: str) -> Path:
        """Export all results for a category to Markdown.

        Args:
            target: Target object
            category: Category ID

        Returns:
            Path to exported file
        """
        output_path = self._get_export_path(
            f"{target.name}_{category}",
            "md"
        )

        # Get all queries for this category
        queries = self.pm.list_queries(target.id)
        category_queries = [q for q in queries if q.category == category]

        # Get all results
        all_results = []
        for query in category_queries:
            results = self.pm.get_results_by_query(query.id)
            all_results.extend([(query, r) for r in results])

        content = self._generate_category_markdown(
            target, category, all_results
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path

    def export_project(self, target: Target) -> Path:
        """Export entire project to Markdown.

        Args:
            target: Target object

        Returns:
            Path to exported file
        """
        output_path = self._get_export_path(
            f"{target.name}_full_report",
            "md"
        )

        # Get all queries and results
        queries = self.pm.list_queries(target.id)

        # Group by category
        categories: Dict[str, List] = {}
        for query in queries:
            if query.category not in categories:
                categories[query.category] = []
            results = self.pm.get_results_by_query(query.id)
            categories[query.category].extend([(query, r) for r in results])

        content = self._generate_project_markdown(target, categories)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path

    def _generate_result_markdown(self, result: Result, query: Optional[Query],
                                  category: str) -> str:
        """Generate Markdown for a single result.

        Args:
            result: Result object
            query: Query object
            category: Category name

        Returns:
            Markdown string
        """
        lines = []
        lines.append("# OSINT-85 Result Export\n")
        lines.append(f"**Exported:** {datetime.now().isoformat()}\n")
        lines.append("---\n")

        # Metadata section
        lines.append("## Metadata\n")
        lines.append(f"- **Category:** {category or 'Unknown'}")
        if query:
            lines.append(f"- **Query:** {query.description}")
            lines.append(f"- **Risk Level:** {query.risk_level}")
        lines.append(f"- **Source:** {result.source_engine or 'Unknown'}")
        lines.append(f"- **Tags:** {result.tags or 'None'}")
        lines.append(f"- **First Seen:** {result.first_seen_at or 'Unknown'}")
        lines.append(f"- **Last Seen:** {result.last_seen_at or 'Unknown'}")
        lines.append("")

        # URL section
        lines.append("## URL\n")
        lines.append(f"```")
        lines.append(result.url)
        lines.append(f"```\n")

        # Title section
        lines.append("## Title\n")
        lines.append(result.title or "*No title*")
        lines.append("")

        # Snippet section
        lines.append("## Snippet\n")
        if result.snippet:
            lines.append("```")
            lines.append(result.snippet)
            lines.append("```")
        else:
            lines.append("*No snippet available*")
        lines.append("")

        # Query details
        if query:
            lines.append("## Query Details\n")
            lines.append(f"**Description:** {query.description}\n")
            lines.append(f"**Query String:**")
            lines.append("```")
            lines.append(query.query)
            lines.append("```")
            lines.append("")

        lines.append("---")
        lines.append(f"*Generated by OSINT-85 v{EXPORT_SCHEMA_VERSION}*")

        return "\n".join(lines)

    def _generate_category_markdown(self, target: Target, category: str,
                                    results: List[tuple]) -> str:
        """Generate Markdown for category results.

        Args:
            target: Target object
            category: Category ID
            results: List of (Query, Result) tuples

        Returns:
            Markdown string
        """
        lines = []
        lines.append(f"# OSINT-85 Category Report: {category}\n")
        lines.append(f"**Target:** {target.name} ({target.primary_domain})")
        lines.append(f"**Exported:** {datetime.now().isoformat()}")
        lines.append(f"**Total Results:** {len(results)}\n")
        lines.append("---\n")

        # Summary
        lines.append("## Summary\n")
        lines.append(f"This report contains {len(results)} results for the **{category}** category.")
        lines.append(f"Target scope: {target.scope or 'Not specified'}\n")

        # Group by query
        query_groups: Dict[int, List] = {}
        for query, result in results:
            if query.id not in query_groups:
                query_groups[query.id] = {"query": query, "results": []}
            query_groups[query.id]["results"].append(result)

        # Results by query
        lines.append("## Results by Query\n")
        for query_id, data in query_groups.items():
            query = data["query"]
            query_results = data["results"]

            lines.append(f"### Query: {query.description}\n")
            lines.append(f"- **Risk Level:** {query.risk_level}")
            lines.append(f"- **Results:** {len(query_results)}")
            lines.append(f"- **Query String:** `{query.query}`\n")

            for i, result in enumerate(query_results, 1):
                lines.append(f"#### Result {i}\n")
                lines.append(f"**URL:** {result.url}\n")
                lines.append(f"**Title:** {result.title or 'No title'}\n")
                if result.tags:
                    lines.append(f"**Tags:** {result.tags}\n")
                if result.snippet:
                    lines.append("**Snippet:**")
                    lines.append("```")
                    lines.append(result.snippet[:200] + ("..." if len(result.snippet) > 200 else ""))
                    lines.append("```\n")
                lines.append("---\n")

        lines.append(f"*Generated by OSINT-85 v{EXPORT_SCHEMA_VERSION}*")

        return "\n".join(lines)

    def _generate_project_markdown(self, target: Target,
                                   categories: Dict[str, List]) -> str:
        """Generate Markdown for entire project.

        Args:
            target: Target object
            categories: Dict of category -> [(Query, Result)] lists

        Returns:
            Markdown string
        """
        total_results = sum(len(results) for results in categories.values())

        lines = []
        lines.append(f"# OSINT-85 Full Project Report\n")
        lines.append(f"**Target:** {target.name}")
        lines.append(f"**Domain:** {target.primary_domain}")
        lines.append(f"**Exported:** {datetime.now().isoformat()}")
        lines.append(f"**Total Results:** {total_results}")
        lines.append(f"**Categories:** {len(categories)}\n")
        lines.append("---\n")

        # Executive Summary
        lines.append("## Executive Summary\n")
        lines.append(f"This comprehensive report contains OSINT reconnaissance results for **{target.name}**.")
        if target.notes:
            lines.append(f"\n**Target Notes:** {target.notes}")
        lines.append(f"\n**Scope:** {target.scope or 'Not specified'}\n")

        # Table of Contents
        lines.append("## Table of Contents\n")
        for i, category in enumerate(categories.keys(), 1):
            lines.append(f"{i}. [{category}](#{category.replace('_', '-')})")
        lines.append("")

        # Categories
        for category, results in categories.items():
            lines.append(f"## {category}\n")
            lines.append(f"**Results in this category:** {len(results)}\n")

            # Group by query
            query_groups: Dict[int, List] = {}
            for query, result in results:
                if query.id not in query_groups:
                    query_groups[query.id] = {"query": query, "results": []}
                query_groups[query.id]["results"].append(result)

            for query_id, data in query_groups.items():
                query = data["query"]
                query_results = data["results"]

                lines.append(f"### {query.description}\n")
                lines.append(f"- **Risk:** {query.risk_level}")
                lines.append(f"- **Results:** {len(query_results)}\n")

                for i, result in enumerate(query_results[:10], 1):  # Limit to 10 per query
                    lines.append(f"**{i}.** [{result.title or result.url}]({result.url})")
                    if result.tags:
                        lines.append(f"   - Tags: {result.tags}")

                if len(query_results) > 10:
                    lines.append(f"\n*...and {len(query_results) - 10} more results*")

                lines.append("")

            lines.append("---\n")

        lines.append(f"*Generated by OSINT-85 v{EXPORT_SCHEMA_VERSION}*")

        return "\n".join(lines)


class JSONExporter(Exporter):
    """Export results to JSON format with stable schema."""

    def export_result(self, result: Result, query: Optional[Query] = None,
                     category: str = "") -> Path:
        """Export a single result to JSON.

        Args:
            result: Result object to export
            query: Associated Query object (optional)
            category: Category name (optional)

        Returns:
            Path to exported file
        """
        output_path = self._get_export_path(
            result.title or "result",
            "json"
        )

        data = {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "export_type": "single_result",
            "exported_at": datetime.now().isoformat(),
            "result": self._result_to_dict(result),
            "query": self._query_to_dict(query) if query else None,
            "category": category
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_path

    def export_category(self, target: Target, category: str) -> Path:
        """Export all results for a category to JSON.

        Args:
            target: Target object
            category: Category ID

        Returns:
            Path to exported file
        """
        output_path = self._get_export_path(
            f"{target.name}_{category}",
            "json"
        )

        # Get all queries for this category
        queries = self.pm.list_queries(target.id)
        category_queries = [q for q in queries if q.category == category]

        # Get all results with query info
        results_data = []
        for query in category_queries:
            results = self.pm.get_results_by_query(query.id)
            for result in results:
                results_data.append({
                    "result": self._result_to_dict(result),
                    "query": self._query_to_dict(query)
                })

        data = {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "export_type": "category",
            "exported_at": datetime.now().isoformat(),
            "target": self._target_to_dict(target),
            "category": category,
            "total_results": len(results_data),
            "results": results_data
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_path

    def export_project(self, target: Target) -> Path:
        """Export entire project to JSON.

        Args:
            target: Target object

        Returns:
            Path to exported file
        """
        output_path = self._get_export_path(
            f"{target.name}_full_export",
            "json"
        )

        # Get all queries
        queries = self.pm.list_queries(target.id)

        # Group by category
        categories: Dict[str, List] = {}
        total_results = 0

        for query in queries:
            if query.category not in categories:
                categories[query.category] = []

            results = self.pm.get_results_by_query(query.id)
            for result in results:
                categories[query.category].append({
                    "result": self._result_to_dict(result),
                    "query": self._query_to_dict(query)
                })
                total_results += 1

        data = {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "export_type": "full_project",
            "exported_at": datetime.now().isoformat(),
            "target": self._target_to_dict(target),
            "total_results": total_results,
            "total_categories": len(categories),
            "categories": categories
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_path

    def _result_to_dict(self, result: Result) -> Dict[str, Any]:
        """Convert Result to dictionary.

        Args:
            result: Result object

        Returns:
            Dictionary representation
        """
        return {
            "id": result.id,
            "url": result.url,
            "title": result.title,
            "snippet": result.snippet,
            "source_engine": result.source_engine,
            "tags": result.tags.split(",") if result.tags else [],
            "first_seen_at": result.first_seen_at,
            "last_seen_at": result.last_seen_at
        }

    def _query_to_dict(self, query: Query) -> Dict[str, Any]:
        """Convert Query to dictionary.

        Args:
            query: Query object

        Returns:
            Dictionary representation
        """
        return {
            "id": query.id,
            "category": query.category,
            "risk_level": query.risk_level,
            "description": query.description,
            "query": query.query,
            "enabled": query.enabled,
            "created_at": query.created_at
        }

    def _target_to_dict(self, target: Target) -> Dict[str, Any]:
        """Convert Target to dictionary.

        Args:
            target: Target object

        Returns:
            Dictionary representation
        """
        return {
            "id": target.id,
            "name": target.name,
            "primary_domain": target.primary_domain,
            "scope": target.scope,
            "notes": target.notes,
            "created_at": target.created_at
        }


class HTMLExporter(Exporter):
    """Export results to HTML format with embedded CSS."""

    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0d0f12;
            color: #e0e0e0;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #1a1d22;
            border: 2px solid #00d4ff;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.2);
        }}
        h1 {{
            color: #00d4ff;
            border-bottom: 3px solid #00d4ff;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #00d4ff;
            margin-top: 30px;
            margin-bottom: 15px;
            border-left: 4px solid #00d4ff;
            padding-left: 15px;
        }}
        h3 {{
            color: #33ddff;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        .metadata {{
            background: #14161a;
            border-left: 4px solid #ffaa00;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .metadata-item {{
            margin: 8px 0;
        }}
        .metadata-label {{
            color: #ffaa00;
            font-weight: bold;
            display: inline-block;
            min-width: 150px;
        }}
        .url {{
            background: #14161a;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #00d4ff;
            word-wrap: break-word;
            margin: 15px 0;
        }}
        .url a {{
            color: #00d4ff;
            text-decoration: none;
        }}
        .url a:hover {{
            text-decoration: underline;
        }}
        .snippet {{
            background: #14161a;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #888;
            margin: 15px 0;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
        }}
        .result-card {{
            background: #14161a;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 20px;
            margin: 20px 0;
            transition: transform 0.2s;
        }}
        .result-card:hover {{
            transform: translateX(5px);
            border-color: #00d4ff;
        }}
        .tag {{
            display: inline-block;
            background: #00d4ff;
            color: #0d0f12;
            padding: 4px 12px;
            border-radius: 12px;
            margin: 4px;
            font-size: 0.9em;
            font-weight: bold;
        }}
        .tag.high-risk {{
            background: #ff3366;
            color: white;
        }}
        .tag.medium-risk {{
            background: #ffaa00;
            color: #0d0f12;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #333;
            text-align: center;
            color: #888;
            font-size: 0.9em;
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-box {{
            background: #14161a;
            border: 2px solid #00d4ff;
            border-radius: 6px;
            padding: 15px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2em;
            color: #00d4ff;
            font-weight: bold;
        }}
        .stat-label {{
            color: #888;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
        <div class="footer">
            Generated by OSINT-85 v{version} on {timestamp}
        </div>
    </div>
</body>
</html>
"""

    def export_result(self, result: Result, query: Optional[Query] = None,
                     category: str = "") -> Path:
        """Export a single result to HTML.

        Args:
            result: Result object to export
            query: Associated Query object (optional)
            category: Category name (optional)

        Returns:
            Path to exported file
        """
        output_path = self._get_export_path(
            result.title or "result",
            "html"
        )

        content = self._generate_result_html(result, query, category)
        html = self.HTML_TEMPLATE.format(
            title=f"OSINT-85 Result: {result.title or result.url[:50]}",
            content=content,
            version=EXPORT_SCHEMA_VERSION,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def export_category(self, target: Target, category: str) -> Path:
        """Export all results for a category to HTML.

        Args:
            target: Target object
            category: Category ID

        Returns:
            Path to exported file
        """
        output_path = self._get_export_path(
            f"{target.name}_{category}",
            "html"
        )

        # Get all queries for this category
        queries = self.pm.list_queries(target.id)
        category_queries = [q for q in queries if q.category == category]

        # Get all results
        all_results = []
        for query in category_queries:
            results = self.pm.get_results_by_query(query.id)
            all_results.extend([(query, r) for r in results])

        content = self._generate_category_html(target, category, all_results)
        html = self.HTML_TEMPLATE.format(
            title=f"OSINT-85 Category Report: {category}",
            content=content,
            version=EXPORT_SCHEMA_VERSION,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def export_project(self, target: Target) -> Path:
        """Export entire project to HTML.

        Args:
            target: Target object

        Returns:
            Path to exported file
        """
        output_path = self._get_export_path(
            f"{target.name}_full_report",
            "html"
        )

        # Get all queries and results
        queries = self.pm.list_queries(target.id)

        # Group by category
        categories: Dict[str, List] = {}
        for query in queries:
            if query.category not in categories:
                categories[query.category] = []
            results = self.pm.get_results_by_query(query.id)
            categories[query.category].extend([(query, r) for r in results])

        content = self._generate_project_html(target, categories)
        html = self.HTML_TEMPLATE.format(
            title=f"OSINT-85 Full Report: {target.name}",
            content=content,
            version=EXPORT_SCHEMA_VERSION,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def _generate_result_html(self, result: Result, query: Optional[Query],
                              category: str) -> str:
        """Generate HTML content for a single result.

        Args:
            result: Result object
            query: Query object
            category: Category name

        Returns:
            HTML string
        """
        html = []
        html.append("<h1>OSINT-85 Result Export</h1>")

        # Metadata
        html.append('<div class="metadata">')
        html.append('<div class="metadata-item"><span class="metadata-label">Category:</span> {}</div>'.format(category or 'Unknown'))
        if query:
            html.append('<div class="metadata-item"><span class="metadata-label">Query:</span> {}</div>'.format(query.description))
            risk_class = "high-risk" if query.risk_level == "high" else "medium-risk" if query.risk_level == "medium" else ""
            html.append('<div class="metadata-item"><span class="metadata-label">Risk Level:</span> <span class="tag {}">{}</span></div>'.format(risk_class, query.risk_level))
        html.append('<div class="metadata-item"><span class="metadata-label">Source:</span> {}</div>'.format(result.source_engine or 'Unknown'))
        if result.tags:
            tags_html = "".join('<span class="tag">{}</span>'.format(tag.strip()) for tag in result.tags.split(","))
            html.append('<div class="metadata-item"><span class="metadata-label">Tags:</span> {}</div>'.format(tags_html))
        html.append('<div class="metadata-item"><span class="metadata-label">First Seen:</span> {}</div>'.format(result.first_seen_at or 'Unknown'))
        html.append('<div class="metadata-item"><span class="metadata-label">Last Seen:</span> {}</div>'.format(result.last_seen_at or 'Unknown'))
        html.append('</div>')

        # URL
        html.append("<h2>URL</h2>")
        html.append('<div class="url"><a href="{}" target="_blank">{}</a></div>'.format(result.url, result.url))

        # Title
        html.append("<h2>Title</h2>")
        html.append("<p>{}</p>".format(result.title or "<em>No title</em>"))

        # Snippet
        html.append("<h2>Snippet</h2>")
        if result.snippet:
            html.append('<div class="snippet">{}</div>'.format(result.snippet))
        else:
            html.append("<p><em>No snippet available</em></p>")

        # Query details
        if query:
            html.append("<h2>Query Details</h2>")
            html.append("<p><strong>Description:</strong> {}</p>".format(query.description))
            html.append('<div class="snippet">{}</div>'.format(query.query))

        return "\n".join(html)

    def _generate_category_html(self, target: Target, category: str,
                                results: List[tuple]) -> str:
        """Generate HTML content for category results.

        Args:
            target: Target object
            category: Category ID
            results: List of (Query, Result) tuples

        Returns:
            HTML string
        """
        html = []
        html.append("<h1>OSINT-85 Category Report: {}</h1>".format(category))

        # Stats
        html.append('<div class="summary-stats">')
        html.append('<div class="stat-box"><div class="stat-number">{}</div><div class="stat-label">Total Results</div></div>'.format(len(results)))
        html.append('<div class="stat-box"><div class="stat-number">{}</div><div class="stat-label">Target</div></div>'.format(target.name))
        html.append('</div>')

        # Target info
        html.append('<div class="metadata">')
        html.append('<div class="metadata-item"><span class="metadata-label">Primary Domain:</span> {}</div>'.format(target.primary_domain))
        html.append('<div class="metadata-item"><span class="metadata-label">Scope:</span> {}</div>'.format(target.scope or 'Not specified'))
        html.append('</div>')

        # Group by query
        query_groups: Dict[int, List] = {}
        for query, result in results:
            if query.id not in query_groups:
                query_groups[query.id] = {"query": query, "results": []}
            query_groups[query.id]["results"].append(result)

        # Results
        html.append("<h2>Results by Query</h2>")
        for query_id, data in query_groups.items():
            query = data["query"]
            query_results = data["results"]

            html.append("<h3>{}</h3>".format(query.description))
            html.append('<p><strong>Risk:</strong> <span class="tag">{}</span> | <strong>Results:</strong> {}</p>'.format(query.risk_level, len(query_results)))

            for i, result in enumerate(query_results, 1):
                html.append('<div class="result-card">')
                html.append('<h4>Result {}</h4>'.format(i))
                html.append('<div class="url"><a href="{}" target="_blank">{}</a></div>'.format(result.url, result.url))
                html.append('<p><strong>Title:</strong> {}</p>'.format(result.title or 'No title'))
                if result.tags:
                    tags_html = "".join('<span class="tag">{}</span>'.format(tag.strip()) for tag in result.tags.split(","))
                    html.append('<p>{}</p>'.format(tags_html))
                if result.snippet:
                    snippet_preview = result.snippet[:200] + ("..." if len(result.snippet) > 200 else "")
                    html.append('<div class="snippet">{}</div>'.format(snippet_preview))
                html.append('</div>')

        return "\n".join(html)

    def _generate_project_html(self, target: Target,
                               categories: Dict[str, List]) -> str:
        """Generate HTML content for entire project.

        Args:
            target: Target object
            categories: Dict of category -> [(Query, Result)] lists

        Returns:
            HTML string
        """
        total_results = sum(len(results) for results in categories.values())

        html = []
        html.append("<h1>OSINT-85 Full Project Report</h1>")

        # Stats
        html.append('<div class="summary-stats">')
        html.append('<div class="stat-box"><div class="stat-number">{}</div><div class="stat-label">Total Results</div></div>'.format(total_results))
        html.append('<div class="stat-box"><div class="stat-number">{}</div><div class="stat-label">Categories</div></div>'.format(len(categories)))
        html.append('<div class="stat-box"><div class="stat-number">{}</div><div class="stat-label">Target</div></div>'.format(target.name))
        html.append('</div>')

        # Target info
        html.append('<div class="metadata">')
        html.append('<div class="metadata-item"><span class="metadata-label">Name:</span> {}</div>'.format(target.name))
        html.append('<div class="metadata-item"><span class="metadata-label">Domain:</span> {}</div>'.format(target.primary_domain))
        html.append('<div class="metadata-item"><span class="metadata-label">Scope:</span> {}</div>'.format(target.scope or 'Not specified'))
        if target.notes:
            html.append('<div class="metadata-item"><span class="metadata-label">Notes:</span> {}</div>'.format(target.notes))
        html.append('</div>')

        # Categories
        for category, results in categories.items():
            html.append("<h2>{}</h2>".format(category))
            html.append("<p><strong>Results in this category:</strong> {}</p>".format(len(results)))

            # Group by query
            query_groups: Dict[int, List] = {}
            for query, result in results:
                if query.id not in query_groups:
                    query_groups[query.id] = {"query": query, "results": []}
                query_groups[query.id]["results"].append(result)

            for query_id, data in query_groups.items():
                query = data["query"]
                query_results = data["results"]

                html.append("<h3>{}</h3>".format(query.description))
                html.append('<p><strong>Risk:</strong> <span class="tag">{}</span> | <strong>Results:</strong> {}</p>'.format(query.risk_level, len(query_results)))

                # Show first 10 results
                for i, result in enumerate(query_results[:10], 1):
                    html.append('<div class="result-card">')
                    html.append('<div class="url"><a href="{}" target="_blank">{}</a></div>'.format(result.url, result.title or result.url[:80]))
                    if result.tags:
                        tags_html = "".join('<span class="tag">{}</span>'.format(tag.strip()) for tag in result.tags.split(","))
                        html.append('<p>{}</p>'.format(tags_html))
                    html.append('</div>')

                if len(query_results) > 10:
                    html.append('<p><em>...and {} more results</em></p>'.format(len(query_results) - 10))

        return "\n".join(html)


def get_exporter(format: str, project_manager: Optional[ProjectManager] = None):
    """Get an exporter instance for the specified format.

    Args:
        format: Export format (markdown, json, html)
        project_manager: ProjectManager instance (optional)

    Returns:
        Exporter instance

    Raises:
        ValueError: If format is not supported
    """
    if format == ExportFormat.MARKDOWN:
        return MarkdownExporter(project_manager)
    elif format == ExportFormat.JSON:
        return JSONExporter(project_manager)
    elif format == ExportFormat.HTML:
        return HTMLExporter(project_manager)
    else:
        raise ValueError(f"Unsupported export format: {format}")
