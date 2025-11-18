"""
Graph-based visualization and analysis for OSINT-85.

Builds relationship graphs from OSINT results showing connections between
domains, subdomains, URLs, and discovered entities.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Set, Tuple, Optional, Any
from urllib.parse import urlparse
import re
from collections import defaultdict

try:
    import networkx as nx
except ImportError:
    nx = None  # Will be installed as dependency

from .database import Result, Query, Target
from .project import ProjectManager


class NodeType(Enum):
    """Types of nodes in the OSINT graph."""
    DOMAIN = "domain"
    SUBDOMAIN = "subdomain"
    URL = "url"
    EMAIL = "email"
    SOCIAL = "social"
    REPOSITORY = "repository"
    IP_ADDRESS = "ip"
    TECHNOLOGY = "technology"
    CREDENTIAL = "credential"
    PATTERN = "pattern"


class EdgeType(Enum):
    """Types of edges in the OSINT graph."""
    OWNS = "owns"
    HOSTS = "hosts"
    LINKS_TO = "links_to"
    FOUND_BY = "found_by"
    CATEGORY = "category"
    CONTAINS = "contains"
    SIMILAR_TO = "similar_to"
    USES = "uses"


@dataclass
class GraphNode:
    """Represents a node in the OSINT graph."""
    id: str
    type: NodeType
    label: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    risk_score: int = 0  # 0-100
    result_count: int = 0  # Number of results associated

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, GraphNode):
            return False
        return self.id == other.id


@dataclass
class GraphEdge:
    """Represents an edge in the OSINT graph."""
    source: str  # Node ID
    target: str  # Node ID
    type: EdgeType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class OSINTGraph:
    """Graph representation of OSINT reconnaissance results."""

    def __init__(self):
        """Initialize empty OSINT graph."""
        if nx is None:
            raise ImportError("networkx is required for graph visualization. Install with: pip install networkx")

        self.graph = nx.DiGraph()
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        self.graph.add_node(
            node.id,
            type=node.type.value,
            label=node.label,
            risk_score=node.risk_score,
            result_count=node.result_count,
            metadata=node.metadata
        )

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)
        self.graph.add_edge(
            edge.source,
            edge.target,
            type=edge.type.value,
            weight=edge.weight,
            metadata=edge.metadata
        )

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> List[GraphNode]:
        """Get all neighboring nodes."""
        if node_id not in self.graph:
            return []

        neighbor_ids = list(self.graph.neighbors(node_id))
        return [self.nodes[nid] for nid in neighbor_ids if nid in self.nodes]

    def get_paths(self, source_id: str, target_id: str, max_paths: int = 5) -> List[List[str]]:
        """Find paths between two nodes."""
        try:
            paths = list(nx.all_simple_paths(
                self.graph,
                source_id,
                target_id,
                cutoff=5  # Max path length
            ))
            return paths[:max_paths]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_centrality(self) -> Dict[str, float]:
        """Calculate node centrality (importance)."""
        if len(self.graph.nodes) == 0:
            return {}

        try:
            return nx.degree_centrality(self.graph)
        except Exception:
            return {node_id: 0.0 for node_id in self.nodes}

    def get_communities(self) -> List[Set[str]]:
        """Detect communities/clusters in the graph."""
        # Convert to undirected for community detection
        undirected = self.graph.to_undirected()

        try:
            # Use greedy modularity communities
            from networkx.algorithms import community
            communities = community.greedy_modularity_communities(undirected)
            return [set(c) for c in communities]
        except Exception:
            # Fallback: each connected component is a community
            return [set(c) for c in nx.connected_components(undirected)]

    def get_subgraph(self, node_ids: Set[str]) -> 'OSINTGraph':
        """Extract a subgraph containing specific nodes."""
        subgraph = OSINTGraph()

        # Add nodes
        for node_id in node_ids:
            if node_id in self.nodes:
                subgraph.add_node(self.nodes[node_id])

        # Add edges between included nodes
        for edge in self.edges:
            if edge.source in node_ids and edge.target in node_ids:
                subgraph.add_edge(edge)

        return subgraph

    def prune_low_degree(self, min_degree: int = 1) -> 'OSINTGraph':
        """Prune nodes with degree below threshold (zoom out)."""
        # Calculate degrees
        degrees = dict(self.graph.degree())

        # Keep nodes with sufficient connections
        keep_nodes = {
            node_id for node_id, degree in degrees.items()
            if degree >= min_degree
        }

        return self.get_subgraph(keep_nodes)

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "node_types": self._count_by_type(),
            "avg_degree": sum(dict(self.graph.degree()).values()) / max(len(self.nodes), 1),
            "density": nx.density(self.graph),
            "is_connected": nx.is_weakly_connected(self.graph) if len(self.graph) > 0 else False
        }

    def _count_by_type(self) -> Dict[str, int]:
        """Count nodes by type."""
        counts = defaultdict(int)
        for node in self.nodes.values():
            counts[node.type.value] += 1
        return dict(counts)


class GraphBuilder:
    """Builds OSINT graphs from project data."""

    def __init__(self, project_manager: ProjectManager):
        """
        Initialize graph builder.

        Args:
            project_manager: ProjectManager instance
        """
        self.pm = project_manager

    def build_from_target(self, target: Target, category: Optional[str] = None) -> OSINTGraph:
        """
        Build graph from target results.

        Args:
            target: Target to build graph for
            category: Optional category filter

        Returns:
            OSINTGraph instance
        """
        graph = OSINTGraph()

        # Get all results
        results = self.pm.get_all_results(target.id, category=category)
        queries = self.pm.list_queries(target.id)
        query_lookup = {q.id: q for q in queries}

        # Add root domain node
        domain_node = GraphNode(
            id=f"domain:{target.primary_domain}",
            type=NodeType.DOMAIN,
            label=target.primary_domain,
            metadata={"target_name": target.name, "scope": target.scope},
            result_count=len(results)
        )
        graph.add_node(domain_node)

        # Process each result
        for result in results:
            self._add_result_to_graph(graph, result, query_lookup.get(result.query_id), target)

        # Add cross-links based on patterns
        self._add_pattern_links(graph, results)

        return graph

    def _add_result_to_graph(
        self,
        graph: OSINTGraph,
        result: Result,
        query: Optional[Query],
        target: Target
    ) -> None:
        """Add a single result to the graph."""
        # Parse URL
        parsed = urlparse(result.url)
        domain = parsed.netloc
        if not domain:
            return

        # Determine node type and create URL node
        url_node_id = f"url:{result.url}"
        url_node = GraphNode(
            id=url_node_id,
            type=NodeType.URL,
            label=result.url[:50] + "..." if len(result.url) > 50 else result.url,
            metadata={
                "full_url": result.url,
                "title": result.title,
                "snippet": result.snippet,
                "tags": result.tags
            },
            risk_score=self._calculate_risk_score(result),
            result_count=1
        )
        graph.add_node(url_node)

        # Add domain/subdomain hierarchy
        if domain != target.primary_domain:
            # It's a subdomain or different domain
            subdomain_node_id = f"subdomain:{domain}"
            if subdomain_node_id not in graph.nodes:
                subdomain_node = GraphNode(
                    id=subdomain_node_id,
                    type=NodeType.SUBDOMAIN,
                    label=domain,
                    metadata={"full_domain": domain}
                )
                graph.add_node(subdomain_node)

                # Link subdomain to root domain
                if self._is_subdomain_of(domain, target.primary_domain):
                    graph.add_edge(GraphEdge(
                        source=f"domain:{target.primary_domain}",
                        target=subdomain_node_id,
                        type=EdgeType.OWNS
                    ))

            # Link URL to subdomain
            graph.add_edge(GraphEdge(
                source=subdomain_node_id,
                target=url_node_id,
                type=EdgeType.HOSTS
            ))
        else:
            # Link URL directly to root domain
            graph.add_edge(GraphEdge(
                source=f"domain:{target.primary_domain}",
                target=url_node_id,
                type=EdgeType.HOSTS
            ))

        # Add query relationship (found-by)
        if query:
            query_node_id = f"query:{query.id}"
            if query_node_id not in graph.nodes:
                query_node = GraphNode(
                    id=query_node_id,
                    type=NodeType.PATTERN,
                    label=query.description or query.query[:30],
                    metadata={
                        "query": query.query,
                        "category": query.category,
                        "risk_level": query.risk_level
                    }
                )
                graph.add_node(query_node)

            graph.add_edge(GraphEdge(
                source=query_node_id,
                target=url_node_id,
                type=EdgeType.FOUND_BY
            ))

        # Extract and add entities from URL/snippet
        self._extract_entities(graph, result, url_node_id)

    def _extract_entities(self, graph: OSINTGraph, result: Result, url_node_id: str) -> None:
        """Extract entities (emails, repos, etc.) from result."""
        text = f"{result.url} {result.title} {result.snippet}"

        # Extract emails
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        for email in set(emails):
            email_node_id = f"email:{email}"
            if email_node_id not in graph.nodes:
                email_node = GraphNode(
                    id=email_node_id,
                    type=NodeType.EMAIL,
                    label=email,
                    risk_score=60  # Emails are moderately risky
                )
                graph.add_node(email_node)

            graph.add_edge(GraphEdge(
                source=url_node_id,
                target=email_node_id,
                type=EdgeType.CONTAINS
            ))

        # Extract GitHub repos
        repo_pattern = r'github\.com/([A-Za-z0-9_-]+/[A-Za-z0-9_-]+)'
        repos = re.findall(repo_pattern, text)
        for repo in set(repos):
            repo_node_id = f"repo:{repo}"
            if repo_node_id not in graph.nodes:
                repo_node = GraphNode(
                    id=repo_node_id,
                    type=NodeType.REPOSITORY,
                    label=repo,
                    metadata={"platform": "github"}
                )
                graph.add_node(repo_node)

            graph.add_edge(GraphEdge(
                source=url_node_id,
                target=repo_node_id,
                type=EdgeType.LINKS_TO
            ))

        # Extract social media handles
        social_pattern = r'@([A-Za-z0-9_]{1,15})\b'
        handles = re.findall(social_pattern, text)
        for handle in set(handles):
            if len(handle) > 2:  # Skip short matches
                social_node_id = f"social:@{handle}"
                if social_node_id not in graph.nodes:
                    social_node = GraphNode(
                        id=social_node_id,
                        type=NodeType.SOCIAL,
                        label=f"@{handle}"
                    )
                    graph.add_node(social_node)

                graph.add_edge(GraphEdge(
                    source=url_node_id,
                    target=social_node_id,
                    type=EdgeType.CONTAINS
                ))

        # Extract technologies from tags
        if result.tags:
            tech_pattern = r'\b(php|python|java|node|react|angular|vue|docker|kubernetes|aws|gcp|azure)\b'
            technologies = re.findall(tech_pattern, result.tags.lower())
            for tech in set(technologies):
                tech_node_id = f"tech:{tech}"
                if tech_node_id not in graph.nodes:
                    tech_node = GraphNode(
                        id=tech_node_id,
                        type=NodeType.TECHNOLOGY,
                        label=tech.upper()
                    )
                    graph.add_node(tech_node)

                graph.add_edge(GraphEdge(
                    source=url_node_id,
                    target=tech_node_id,
                    type=EdgeType.USES
                ))

    def _add_pattern_links(self, graph: OSINTGraph, results: List[Result]) -> None:
        """Add similarity links between similar results."""
        # Group results by similar URLs (same path structure)
        url_patterns = defaultdict(list)

        for result in results:
            parsed = urlparse(result.url)
            # Create pattern from path
            path_pattern = "/".join(parsed.path.split("/")[:3])  # First 3 path segments
            url_patterns[path_pattern].append(result.url)

        # Add similarity edges for grouped URLs
        for pattern, urls in url_patterns.items():
            if len(urls) > 1:
                # Add edges between similar URLs
                for i, url1 in enumerate(urls):
                    for url2 in urls[i+1:]:
                        node1_id = f"url:{url1}"
                        node2_id = f"url:{url2}"
                        if node1_id in graph.nodes and node2_id in graph.nodes:
                            graph.add_edge(GraphEdge(
                                source=node1_id,
                                target=node2_id,
                                type=EdgeType.SIMILAR_TO,
                                weight=0.5,  # Lower weight for similarity
                                metadata={"pattern": pattern}
                            ))

    def _calculate_risk_score(self, result: Result) -> int:
        """Calculate risk score for a result (0-100)."""
        score = 30  # Base score

        # Increase based on tags
        if result.tags:
            tags_lower = result.tags.lower()
            risk_keywords = {
                "credentials": 40,
                "password": 40,
                "secret": 35,
                "api_key": 35,
                "token": 30,
                "config": 25,
                "backup": 20,
                "admin": 20,
                "database": 15,
                "sensitive": 15
            }

            for keyword, points in risk_keywords.items():
                if keyword in tags_lower:
                    score += points

        # Cap at 100
        return min(score, 100)

    def _is_subdomain_of(self, subdomain: str, domain: str) -> bool:
        """Check if subdomain is a subdomain of domain."""
        return subdomain.endswith(f".{domain}") or subdomain == domain


class GraphLayout:
    """Calculate node positions for graph visualization."""

    @staticmethod
    def force_directed(graph: OSINTGraph, iterations: int = 50) -> Dict[str, Tuple[float, float]]:
        """
        Calculate force-directed layout.

        Args:
            graph: OSINTGraph instance
            iterations: Number of iterations for layout algorithm

        Returns:
            Dictionary mapping node IDs to (x, y) positions
        """
        if len(graph.nodes) == 0:
            return {}

        try:
            pos = nx.spring_layout(
                graph.graph,
                iterations=iterations,
                k=1.0,  # Optimal distance between nodes
                scale=100  # Scale positions
            )
            return {node_id: (float(x), float(y)) for node_id, (x, y) in pos.items()}
        except Exception:
            # Fallback: simple grid layout
            return GraphLayout.grid(graph)

    @staticmethod
    def hierarchical(graph: OSINTGraph) -> Dict[str, Tuple[float, float]]:
        """
        Calculate hierarchical layout (top-down tree).

        Args:
            graph: OSINTGraph instance

        Returns:
            Dictionary mapping node IDs to (x, y) positions
        """
        if len(graph.nodes) == 0:
            return {}

        try:
            # Use graphviz dot layout if available
            pos = nx.nx_agraph.graphviz_layout(graph.graph, prog="dot")
            return {node_id: (float(x), float(y)) for node_id, (x, y) in pos.items()}
        except Exception:
            # Fallback: manual hierarchical layout
            return GraphLayout._manual_hierarchical(graph)

    @staticmethod
    def _manual_hierarchical(graph: OSINTGraph) -> Dict[str, Tuple[float, float]]:
        """Manual hierarchical layout fallback."""
        positions = {}
        levels = defaultdict(list)

        # BFS to assign levels
        if not graph.nodes:
            return positions

        # Find root nodes (nodes with no incoming edges)
        roots = [
            node_id for node_id in graph.nodes
            if graph.graph.in_degree(node_id) == 0
        ]

        if not roots:
            # No clear roots, use first node
            roots = [list(graph.nodes.keys())[0]]

        # BFS from roots
        visited = set()
        queue = [(root, 0) for root in roots]

        while queue:
            node_id, level = queue.pop(0)
            if node_id in visited:
                continue

            visited.add(node_id)
            levels[level].append(node_id)

            # Add neighbors to queue
            for neighbor in graph.graph.neighbors(node_id):
                if neighbor not in visited:
                    queue.append((neighbor, level + 1))

        # Assign positions
        for level, nodes in levels.items():
            for i, node_id in enumerate(nodes):
                x = (i - len(nodes) / 2) * 20
                y = level * 15
                positions[node_id] = (x, y)

        return positions

    @staticmethod
    def grid(graph: OSINTGraph) -> Dict[str, Tuple[float, float]]:
        """Simple grid layout."""
        positions = {}
        node_ids = list(graph.nodes.keys())

        grid_size = int(len(node_ids) ** 0.5) + 1

        for i, node_id in enumerate(node_ids):
            x = (i % grid_size) * 20
            y = (i // grid_size) * 15
            positions[node_id] = (float(x), float(y))

        return positions
