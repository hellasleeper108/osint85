import pytest
from unittest.mock import MagicMock, patch
from osint85.graph_view import GraphCanvas, GraphView
from osint85.graph import OSINTGraph, GraphNode, NodeType

class TestGraphCanvas:
    @pytest.fixture
    def canvas(self):
        return GraphCanvas()

    def test_set_graph(self, canvas):
        graph = OSINTGraph()
        graph.add_node(GraphNode("1", NodeType.DOMAIN, "test"))
        
        canvas.set_graph(graph, layout_type="grid")
        assert canvas.graph == graph
        assert len(canvas.positions) == 1

    def test_zoom(self, canvas):
        initial_zoom = canvas.zoom_level
        canvas.zoom_in()
        assert canvas.zoom_level > initial_zoom
        
        canvas.zoom_out()
        assert canvas.zoom_level == initial_zoom

    def test_pan(self, canvas):
        canvas.pan(10, 20)
        assert canvas.offset_x == 10
        assert canvas.offset_y == 20

    def test_transform_positions(self, canvas):
        graph = OSINTGraph()
        graph.add_node(GraphNode("1", NodeType.DOMAIN, "test"))
        canvas.set_graph(graph, layout_type="grid")
        
        # Mock size - removed as _transform_positions takes width/height args
        
        screen_pos = canvas._transform_positions(100, 100)
        assert len(screen_pos) == 1

class TestGraphView:
    @pytest.fixture
    def mock_pm(self):
        return MagicMock()

    def test_initialization(self, mock_pm):
        view = GraphView(mock_pm)
        assert view.pm == mock_pm
        assert isinstance(view.canvas, GraphCanvas)

    def test_load_graph(self, mock_pm):
        view = GraphView(mock_pm)
        
        # Mock target and builder
        mock_target = MagicMock()
        mock_pm.get_target.return_value = mock_target
        
        with patch('osint85.graph.GraphBuilder') as MockBuilder:
            mock_builder = MockBuilder.return_value
            mock_builder.build_from_target.return_value = OSINTGraph()
            
            view.load_graph(1)
            
            mock_pm.get_target.assert_called_with(1)
            mock_builder.build_from_target.assert_called()
            assert view.canvas.graph is not None
