"""LLM-powered dork query generation for osint85."""

import json
from typing import List, Dict, Any

from .llm_client import get_llm_client, parse_json_response
from .database import Target


# System prompt for dork generation
DORK_GENERATION_SYSTEM_PROMPT = """You generate advanced search-operator queries for open-source reconnaissance and defensive security.
You only generate queries and short metadata in pure JSON.
Never include instructions, prose, or comments.

The user will provide:
1. Target profile (name, domain, notes, scope)
2. A goal, such as "map login portals" or "find exposed backups"

Respond strictly as:
{
  "queries": [
    {
      "category": "string",
      "risk_level": "low|medium|high",
      "description": "short human description",
      "query": "search operator query string here"
    }
  ]
}

Categories should be one of: exposed_directories, exposed_backups, config_files, staging_environments, login_portals, debug_endpoints, api_endpoints, test_files, sensitive_documents, code_repositories, other

Risk levels:
- low: Informational findings, public data
- medium: Potentially sensitive but not critical
- high: Critical exposure (backups, configs, credentials)

Generate 5-15 queries depending on the goal complexity.
Use advanced search operators like site:, inurl:, intitle:, filetype:, ext:, etc.
Be creative and thorough."""


class DorkGenerator:
    """Generates dork-style search queries using LLM."""

    def __init__(self, llm_provider: str = None):
        """Initialize dork generator.

        Args:
            llm_provider: LLM provider to use (defaults to config)
        """
        self.llm_client = get_llm_client(llm_provider)

    def generate(self, target: Target, goal: str) -> List[Dict[str, Any]]:
        """Generate dork queries for a target and goal.

        Args:
            target: Target object with profile information
            goal: User's goal (e.g., "Find exposed backups")

        Returns:
            List of query dictionaries

        Raises:
            RuntimeError: If LLM generation fails
            ValueError: If response is invalid
        """
        # Construct user prompt
        user_prompt = json.dumps({
            "target": {
                "name": target.name,
                "primary_domain": target.primary_domain,
                "scope": target.scope,
                "notes": target.notes
            },
            "goal": goal
        }, indent=2)

        # Generate queries
        try:
            response = self.llm_client.generate(
                system_prompt=DORK_GENERATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=3000
            )
        except Exception as e:
            raise RuntimeError(f"Failed to generate dorks: {e}") from e

        # Parse JSON response
        try:
            parsed = parse_json_response(response)
            queries = parsed.get("queries", [])

            if not queries:
                raise ValueError("No queries generated")

            # Validate query structure
            for q in queries:
                if not all(k in q for k in ["category", "risk_level", "description", "query"]):
                    raise ValueError(f"Invalid query structure: {q}")

            return queries

        except (ValueError, KeyError) as e:
            raise ValueError(f"Failed to parse LLM response: {e}\nResponse: {response}") from e

    def generate_for_categories(self, target: Target, categories: List[str]) -> List[Dict[str, Any]]:
        """Generate dork queries for specific categories.

        Args:
            target: Target object
            categories: List of category names

        Returns:
            List of query dictionaries
        """
        goal = f"Generate search queries for the following categories: {', '.join(categories)}"
        return self.generate(target, goal)

    def generate_comprehensive(self, target: Target) -> List[Dict[str, Any]]:
        """Generate a comprehensive set of dork queries covering all common categories.

        Args:
            target: Target object

        Returns:
            List of query dictionaries
        """
        goal = """Generate a comprehensive set of reconnaissance queries covering:
- Exposed directories and file listings
- Backup files and archives
- Configuration files
- Staging and development environments
- Login portals and admin panels
- Debug and error pages
- API endpoints and documentation
- Test files and development artifacts
- Sensitive documents (PDF, DOC, XLS)
- Code repositories and version control"""

        return self.generate(target, goal)
