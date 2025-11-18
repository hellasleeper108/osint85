"""LLM-powered report generation for osint85."""

import json
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from .llm_client import get_llm_client
from .database import Target, Query, Result
from .project import ProjectManager


# System prompt for report generation
REPORT_GENERATION_SYSTEM_PROMPT = """You are a defensive security analyst.
You receive a list of URLs & snippets that came from advanced search queries during OSINT reconnaissance.

Your job is to:
1. Group results by category (backups, configs, panels, testing endpoints, staging, misc)
2. Describe what each group might imply from a security perspective
3. Suggest safe, high-level mitigation steps from a defensive perspective

Respond in markdown format.
Be concise and professional.
Do NOT include exploitation steps or attack techniques.
This is for internal security audit and awareness, not for offensive use.

Structure your response as:
# OSINT Reconnaissance Report

## Executive Summary
[Brief overview of findings]

## Findings by Category

### [Category Name]
**Risk Level:** [Low/Medium/High]

**URLs Found:**
- [url] - [brief description from snippet]

**Security Implications:**
[What this might mean]

**Recommendations:**
- [Defensive mitigation steps]

[Repeat for each category]

## Overall Recommendations
[General security improvements]
"""


class Reporter:
    """Generates reports from search results using LLM."""

    def __init__(self, project_manager: ProjectManager, llm_provider: str = None):
        """Initialize reporter.

        Args:
            project_manager: ProjectManager instance
            llm_provider: LLM provider to use (defaults to config)
        """
        self.pm = project_manager
        self.llm_client = get_llm_client(llm_provider)

    def generate(self, target: Target, out_path: str = None) -> str:
        """Generate a comprehensive report for a target.

        Args:
            target: Target object
            out_path: Output file path (optional)

        Returns:
            Report markdown content
        """
        # Get all results for the target
        results = self.pm.get_all_results(target.id)

        if not results:
            report = f"# OSINT Report for {target.name}\n\nNo results found."
            if out_path:
                Path(out_path).write_text(report, encoding="utf-8")
            return report

        # Get queries to map results to categories
        queries = self.pm.list_queries(target.id)
        query_map = {q.id: q for q in queries}

        # Group results by category
        results_by_category = self._group_by_category(results, query_map)

        # Prepare data for LLM
        llm_input = self._prepare_llm_input(target, results_by_category)

        # Generate report using LLM
        try:
            report = self.llm_client.generate(
                system_prompt=REPORT_GENERATION_SYSTEM_PROMPT,
                user_prompt=llm_input,
                max_tokens=4000
            )
        except Exception as e:
            # Fallback to basic report if LLM fails
            print(f"[WARNING] LLM report generation failed: {e}")
            report = self._generate_basic_report(target, results_by_category)

        # Add metadata header
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"""---
Generated: {timestamp}
Target: {target.name}
Domain: {target.primary_domain}
Total Results: {len(results)}
---

"""
        report = header + report

        # Save to file if requested
        if out_path:
            output_file = Path(out_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(report, encoding="utf-8")
            print(f"Report saved to: {out_path}")

        return report

    def _group_by_category(self, results: List[Result], query_map: Dict[int, Query]) -> Dict[str, List[Result]]:
        """Group results by query category.

        Args:
            results: List of Result objects
            query_map: Mapping of query_id to Query object

        Returns:
            Dictionary mapping category to list of results
        """
        grouped = defaultdict(list)

        for result in results:
            query = query_map.get(result.query_id)
            if query:
                category = query.category
                grouped[category].append(result)
            else:
                grouped["uncategorized"].append(result)

        return dict(grouped)

    def _prepare_llm_input(self, target: Target, results_by_category: Dict[str, List[Result]]) -> str:
        """Prepare input data for LLM.

        Args:
            target: Target object
            results_by_category: Results grouped by category

        Returns:
            JSON string for LLM input
        """
        data = {
            "target": {
                "name": target.name,
                "domain": target.primary_domain,
                "scope": target.scope
            },
            "findings": {}
        }

        for category, results in results_by_category.items():
            data["findings"][category] = [
                {
                    "url": r.url,
                    "title": r.title,
                    "snippet": r.snippet[:200],  # Truncate long snippets
                    "tags": r.tags
                }
                for r in results[:20]  # Limit to 20 results per category
            ]

        return json.dumps(data, indent=2)

    def _generate_basic_report(self, target: Target, results_by_category: Dict[str, List[Result]]) -> str:
        """Generate a basic report without LLM (fallback).

        Args:
            target: Target object
            results_by_category: Results grouped by category

        Returns:
            Markdown report
        """
        report = f"# OSINT Report for {target.name}\n\n"
        report += f"**Domain:** {target.primary_domain}\n\n"

        if target.scope:
            report += f"**Scope:** {target.scope}\n\n"

        report += "---\n\n"
        report += "## Findings by Category\n\n"

        for category, results in sorted(results_by_category.items()):
            report += f"### {category.replace('_', ' ').title()}\n\n"
            report += f"**Total Results:** {len(results)}\n\n"
            report += "**URLs:**\n"

            for i, result in enumerate(results[:15], 1):  # Limit to 15 per category
                report += f"{i}. [{result.title or 'No title'}]({result.url})\n"
                if result.snippet:
                    report += f"   - {result.snippet[:150]}...\n"
                if result.tags:
                    report += f"   - Tags: `{result.tags}`\n"

            report += "\n"

        report += "---\n\n"
        report += "## Recommendations\n\n"
        report += "- Review all findings for unauthorized exposure\n"
        report += "- Remove or secure any exposed backups, configs, or debug endpoints\n"
        report += "- Implement proper access controls on staging/dev environments\n"
        report += "- Use robots.txt and authentication to protect sensitive areas\n"
        report += "- Regular security scans to catch new exposures\n"

        return report

    def generate_summary(self, target: Target) -> str:
        """Generate a quick summary of findings.

        Args:
            target: Target object

        Returns:
            Summary text
        """
        results = self.pm.get_all_results(target.id)
        queries = self.pm.list_queries(target.id)

        summary = f"**Target:** {target.name} ({target.primary_domain})\n"
        summary += f"**Queries:** {len(queries)} total, {len([q for q in queries if q.enabled])} enabled\n"
        summary += f"**Results:** {len(results)} total\n"

        # Count by tags
        tag_counts = defaultdict(int)
        for result in results:
            if result.tags:
                for tag in result.tags.split(","):
                    tag_counts[tag.strip()] += 1

        if tag_counts:
            summary += "\n**Results by Tag:**\n"
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
                summary += f"- {tag}: {count}\n"

        return summary
