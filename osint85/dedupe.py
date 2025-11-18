"""Deduplication engine for OSINT-85 results."""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs, urljoin
import re

from rapidfuzz import fuzz

from .database import Result
from .project import ProjectManager


@dataclass
class DuplicateGroup:
    """Represents a group of duplicate results."""
    primary: Result
    duplicates: List[Result]
    similarity_scores: Dict[int, float]  # result_id -> score


class URLNormalizer:
    """Normalizes URLs for comparison."""

    @staticmethod
    def normalize(url: str) -> str:
        """Normalize a URL for comparison.

        Removes common variations that don't change the resource:
        - Trailing slashes
        - Common tracking parameters
        - URL fragments
        - Protocol differences (http vs https)
        - www subdomain

        Args:
            url: URL to normalize

        Returns:
            Normalized URL string
        """
        # Parse URL
        parsed = urlparse(url.lower().strip())

        # Remove protocol (http/https are equivalent for deduplication)
        scheme = ""

        # Remove www subdomain
        netloc = parsed.netloc
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Remove trailing slash from path
        path = parsed.path.rstrip("/")

        # Remove common tracking parameters
        tracking_params = {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "fbclid", "gclid", "msclkid", "ref", "source", "campaign"
        }

        query_params = parse_qs(parsed.query)
        filtered_params = {
            k: v for k, v in query_params.items()
            if k.lower() not in tracking_params
        }

        # Rebuild query string
        if filtered_params:
            query = "&".join(
                f"{k}={v[0]}" for k, v in sorted(filtered_params.items())
            )
        else:
            query = ""

        # Ignore fragments (anchors)
        fragment = ""

        # Rebuild URL
        normalized = f"{netloc}{path}"
        if query:
            normalized += f"?{query}"

        return normalized

    @staticmethod
    def get_domain(url: str) -> str:
        """Extract domain from URL.

        Args:
            url: URL to extract domain from

        Returns:
            Domain string
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain


class DeduplicationEngine:
    """Engine for detecting and managing duplicate results."""

    def __init__(self, project_manager: Optional[ProjectManager] = None,
                 fuzzy_threshold: float = 90.0):
        """Initialize deduplication engine.

        Args:
            project_manager: ProjectManager instance
            fuzzy_threshold: Similarity threshold for fuzzy matching (0-100)
        """
        self.pm = project_manager or ProjectManager()
        self.fuzzy_threshold = fuzzy_threshold
        self.normalizer = URLNormalizer()

    def find_duplicates(self, results: List[Result]) -> List[DuplicateGroup]:
        """Find duplicate results in a list.

        Args:
            results: List of Result objects to analyze

        Returns:
            List of DuplicateGroup objects
        """
        if not results:
            return []

        # First pass: exact URL matches (after normalization)
        url_groups = self._group_by_exact_url(results)

        # Second pass: fuzzy matching within same domain
        duplicate_groups = []

        for primary, exact_duplicates in url_groups:
            group = DuplicateGroup(
                primary=primary,
                duplicates=exact_duplicates,
                similarity_scores={d.id: 100.0 for d in exact_duplicates}
            )
            duplicate_groups.append(group)

        # Find fuzzy duplicates
        fuzzy_groups = self._find_fuzzy_duplicates(results)

        # Merge fuzzy groups
        for group in fuzzy_groups:
            # Check if primary is already in a group
            existing_group = None
            for dg in duplicate_groups:
                if dg.primary.id == group.primary.id:
                    existing_group = dg
                    break

            if existing_group:
                # Add fuzzy duplicates to existing group
                for dup in group.duplicates:
                    if dup.id not in [d.id for d in existing_group.duplicates]:
                        existing_group.duplicates.append(dup)
                        existing_group.similarity_scores[dup.id] = group.similarity_scores[dup.id]
            else:
                duplicate_groups.append(group)

        return duplicate_groups

    def _group_by_exact_url(self, results: List[Result]) -> List[Tuple[Result, List[Result]]]:
        """Group results by exact normalized URL.

        Args:
            results: List of Result objects

        Returns:
            List of (primary, duplicates) tuples
        """
        url_map: Dict[str, List[Result]] = {}

        for result in results:
            normalized = self.normalizer.normalize(result.url)

            if normalized not in url_map:
                url_map[normalized] = []

            url_map[normalized].append(result)

        # For each group, select primary (highest score or earliest)
        groups = []
        for normalized_url, group_results in url_map.items():
            if len(group_results) > 1:
                # Select primary (prefer earlier ID as a tiebreaker)
                primary = min(group_results, key=lambda r: r.id or float('inf'))
                duplicates = [r for r in group_results if r.id != primary.id]
                groups.append((primary, duplicates))

        return groups

    def _find_fuzzy_duplicates(self, results: List[Result]) -> List[DuplicateGroup]:
        """Find fuzzy duplicate URLs using similarity scoring.

        Args:
            results: List of Result objects

        Returns:
            List of DuplicateGroup objects
        """
        groups = []

        # Group by domain for efficiency
        domain_groups: Dict[str, List[Result]] = {}
        for result in results:
            domain = self.normalizer.get_domain(result.url)
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(result)

        # Find fuzzy duplicates within each domain
        for domain, domain_results in domain_groups.items():
            if len(domain_results) < 2:
                continue

            # Compare each pair
            checked = set()

            for i, result1 in enumerate(domain_results):
                if result1.id in checked:
                    continue

                duplicates = []
                scores = {}

                normalized1 = self.normalizer.normalize(result1.url)

                for j, result2 in enumerate(domain_results):
                    if i == j or result2.id in checked:
                        continue

                    normalized2 = self.normalizer.normalize(result2.url)

                    # Calculate similarity
                    similarity = fuzz.ratio(normalized1, normalized2)

                    if similarity >= self.fuzzy_threshold:
                        duplicates.append(result2)
                        scores[result2.id] = similarity
                        checked.add(result2.id)

                if duplicates:
                    group = DuplicateGroup(
                        primary=result1,
                        duplicates=duplicates,
                        similarity_scores=scores
                    )
                    groups.append(group)
                    checked.add(result1.id)

        return groups

    def mark_duplicates(self, target_id: int, category: Optional[str] = None) -> int:
        """Mark duplicate results in the database.

        Args:
            target_id: Target/project ID
            category: Specific category to deduplicate (optional)

        Returns:
            Number of results marked as duplicates
        """
        # Get all results
        if category:
            queries = self.pm.list_queries(target_id)
            category_query_ids = [q.id for q in queries if q.category == category]
            results = []
            for qid in category_query_ids:
                results.extend(self.pm.get_results_by_query(qid))
        else:
            results = self.pm.get_all_results(target_id)

        if not results:
            return 0

        # Find duplicates
        duplicate_groups = self.find_duplicates(results)

        # Mark in database
        marked_count = 0

        for group in duplicate_groups:
            for duplicate in group.duplicates:
                similarity = group.similarity_scores.get(duplicate.id, 100.0)

                # Update duplicate in database
                self.pm.mark_as_duplicate(
                    result_id=duplicate.id,
                    duplicate_of_id=group.primary.id,
                    similarity_score=similarity
                )
                marked_count += 1

        return marked_count

    def get_duplicate_stats(self, target_id: int) -> Dict[str, int]:
        """Get statistics about duplicates in a project.

        Args:
            target_id: Target/project ID

        Returns:
            Dictionary with duplicate statistics
        """
        all_results = self.pm.get_all_results(target_id)

        total_results = len(all_results)
        duplicate_results = len([r for r in all_results if hasattr(r, 'is_duplicate') and r.is_duplicate])
        unique_results = total_results - duplicate_results

        # Find groups
        groups = self.find_duplicates(all_results)
        duplicate_groups = len(groups)

        return {
            "total_results": total_results,
            "unique_results": unique_results,
            "duplicate_results": duplicate_results,
            "duplicate_groups": duplicate_groups
        }

    def remove_duplicates(self, target_id: int, category: Optional[str] = None) -> int:
        """Remove duplicate results from database.

        Args:
            target_id: Target/project ID
            category: Specific category to clean (optional)

        Returns:
            Number of duplicates removed
        """
        # First mark duplicates
        self.mark_duplicates(target_id, category)

        # Get all marked duplicates
        if category:
            queries = self.pm.list_queries(target_id)
            category_query_ids = [q.id for q in queries if q.category == category]
            results = []
            for qid in category_query_ids:
                results.extend(self.pm.get_results_by_query(qid))
        else:
            results = self.pm.get_all_results(target_id)

        # Delete duplicates
        removed_count = 0
        for result in results:
            if hasattr(result, 'is_duplicate') and result.is_duplicate:
                self.pm.delete_result(result.id)
                removed_count += 1

        return removed_count


def calculate_url_similarity(url1: str, url2: str) -> float:
    """Calculate similarity between two URLs.

    Args:
        url1: First URL
        url2: Second URL

    Returns:
        Similarity score (0-100)
    """
    normalizer = URLNormalizer()
    norm1 = normalizer.normalize(url1)
    norm2 = normalizer.normalize(url2)

    return fuzz.ratio(norm1, norm2)


def is_duplicate_url(url1: str, url2: str, threshold: float = 90.0) -> bool:
    """Check if two URLs are duplicates.

    Args:
        url1: First URL
        url2: Second URL
        threshold: Similarity threshold (0-100)

    Returns:
        True if URLs are duplicates
    """
    similarity = calculate_url_similarity(url1, url2)
    return similarity >= threshold
