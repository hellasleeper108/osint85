import pytest
from unittest.mock import MagicMock, patch
from osint85.graph import OSINTGraph, GraphNode, GraphEdge, NodeType, EdgeType, GraphBuilder, GraphLayout
from osint85.database import Result, Query, Target

class TestOSINTGraph:
    @pytest.fixture
    def graph(self):
        return OSINTGraph()

    def test_add_node(self, graph):
        node = GraphNode("1", NodeType.DOMAIN, "example.com")
        graph.add_node(node)
        assert "1" in graph.nodes
        assert graph.get_node("1") == node

    def test_add_edge(self, graph):
        node1 = GraphNode("1", NodeType.DOMAIN, "example.com")
        node2 = GraphNode("2", NodeType.URL, "http://example.com")
        graph.add_node(node1)
        graph.add_node(node2)
        
        edge = GraphEdge("1", "2", EdgeType.HOSTS)
        graph.add_edge(edge)
        assert len(graph.edges) == 1

    def test_get_neighbors(self, graph):
        node1 = GraphNode("1", NodeType.DOMAIN, "example.com")
        node2 = GraphNode("2", NodeType.URL, "http://example.com")
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_edge(GraphEdge("1", "2", EdgeType.HOSTS))
        
        neighbors = graph.get_neighbors("1")
        assert len(neighbors) == 1
        assert neighbors[0] == node2

    def test_get_stats(self, graph):
        node = GraphNode("1", NodeType.DOMAIN, "example.com")
        graph.add_node(node)
        stats = graph.get_stats()
        assert stats["node_count"] == 1
        assert stats["node_types"]["domain"] == 1

class TestGraphBuilder:
    @pytest.fixture
    def mock_pm(self):
        return MagicMock()

    def test_build_from_target(self, mock_pm):
        target = Target(id=1, name="Test", primary_domain="example.com", created_at="now")
        mock_pm.get_all_results.return_value = []
        mock_pm.list_queries.return_value = []
        
        builder = GraphBuilder(mock_pm)
        graph = builder.build_from_target(target)
        
        assert len(graph.nodes) == 1
        assert "domain:example.com" in graph.nodes

    def test_add_result_to_graph(self, mock_pm):
        target = Target(id=1, name="Test", primary_domain="example.com", created_at="now")
        result = Result(id=1, query_id=1, url="http://sub.example.com", title="Test", 
                        snippet="test@example.com", source_engine="google", tags="tag", 
                        first_seen_at="now", last_seen_at="now")
        query = Query(id=1, target_id=1, category="test", risk_level="high", 
                      description="desc", query="query", enabled=True, created_at="now")
        
        mock_pm.get_all_results.return_value = [result]
        mock_pm.list_queries.return_value = [query]
        
        builder = GraphBuilder(mock_pm)
        graph = builder.build_from_target(target)
        
        # Should have domain, subdomain, url, email, query nodes
        assert len(graph.nodes) >= 5
        assert "email:test@example.com" in graph.nodes

class TestGraphLayout:
    def test_grid_layout(self):
        graph = OSINTGraph()
        graph.add_node(GraphNode("1", NodeType.DOMAIN, "1"))
        graph.add_node(GraphNode("2", NodeType.DOMAIN, "2"))
        
        pos = GraphLayout.grid(graph)
        assert len(pos) == 2
        assert "1" in pos
        assert "2" in pos
