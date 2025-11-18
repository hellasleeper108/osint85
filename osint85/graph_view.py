"""
Graph visualization widget for OSINT-85 TUI.

Provides interactive terminal-based graph visualization with zoom, pan, and highlighting.
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, Label
from textual.reactive import reactive
from textual import events
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from typing import Dict, Tuple, Set, Optional, List
import math

from .graph import OSINTGraph, GraphNode, GraphLayout, NodeType, EdgeType
from .project import ProjectManager


class GraphCanvas(Static):
    """Canvas for rendering the graph."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph: Optional[OSINTGraph] = None
        self.positions: Dict[str, Tuple[float, float]] = {}
        self.zoom_level: float = 1.0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.highlighted_paths: List[List[str]] = []
        self.selected_node: Optional[str] = None

    def set_graph(self, graph: OSINTGraph, layout_type: str = "force"):
        """Set the graph to display."""
        self.graph = graph

        # Calculate layout
        if layout_type == "hierarchical":
            self.positions = GraphLayout.hierarchical(graph)
        elif layout_type == "grid":
            self.positions = GraphLayout.grid(graph)
        else:  # force-directed
            self.positions = GraphLayout.force_directed(graph)

        # Center the graph
        if self.positions:
            self._center_graph()

        self.refresh()

    def _center_graph(self):
        """Center the graph in the viewport."""
        if not self.positions:
            return

        # Find bounds
        xs = [x for x, y in self.positions.values()]
        ys = [y for x, y in self.positions.values()]

        if xs and ys:
            center_x = (min(xs) + max(xs)) / 2
            center_y = (min(ys) + max(ys)) / 2

            # Offset to center (0, 0)
            self.offset_x = -center_x
            self.offset_y = -center_y

    def zoom_in(self):
        """Zoom in (increase zoom level)."""
        self.zoom_level = min(self.zoom_level * 1.2, 5.0)
        self.refresh()

    def zoom_out(self):
        """Zoom out (decrease zoom level)."""
        self.zoom_level = max(self.zoom_level / 1.2, 0.2)
        self.refresh()

    def pan(self, dx: float, dy: float):
        """Pan the view."""
        self.offset_x += dx / self.zoom_level
        self.offset_y += dy / self.zoom_level
        self.refresh()

    def highlight_path(self, path: List[str]):
        """Highlight a path in the graph."""
        self.highlighted_paths = [path]
        self.refresh()

    def select_node(self, node_id: str):
        """Select a node."""
        self.selected_node = node_id
        self.refresh()

    def render(self) -> Text:
        """Render the graph as ASCII art."""
        if not self.graph or not self.positions:
            return Text("No graph data to display", style="dim")

        # Get canvas size
        width = self.size.width if self.size else 100
        height = self.size.height if self.size else 30

        # Create ASCII canvas
        canvas = [[' ' for _ in range(width)] for _ in range(height)]
        colors = [[None for _ in range(width)] for _ in range(height)]

        # Transform positions to screen coordinates
        screen_positions = self._transform_positions(width, height)

        # Draw edges first (so nodes appear on top)
        self._draw_edges(canvas, colors, screen_positions)

        # Draw nodes
        self._draw_nodes(canvas, colors, screen_positions)

        # Convert canvas to Rich Text
        return self._canvas_to_text(canvas, colors)

    def _transform_positions(self, width: int, height: int) -> Dict[str, Tuple[int, int]]:
        """Transform graph positions to screen coordinates."""
        screen_pos = {}

        for node_id, (x, y) in self.positions.items():
            # Apply zoom and offset
            screen_x = (x + self.offset_x) * self.zoom_level
            screen_y = (y + self.offset_y) * self.zoom_level

            # Convert to screen coordinates (center origin)
            sx = int(screen_x + width / 2)
            sy = int(screen_y + height / 2)

            # Only include if within bounds
            if 0 <= sx < width and 0 <= sy < height:
                screen_pos[node_id] = (sx, sy)

        return screen_pos

    def _draw_edges(self, canvas, colors, screen_positions):
        """Draw edges on the canvas."""
        if not self.graph:
            return

        # Get highlighted nodes
        highlighted_nodes = set()
        for path in self.highlighted_paths:
            highlighted_nodes.update(path)

        for edge in self.graph.edges:
            if edge.source not in screen_positions or edge.target not in screen_positions:
                continue

            x1, y1 = screen_positions[edge.source]
            x2, y2 = screen_positions[edge.target]

            # Determine edge style
            is_highlighted = edge.source in highlighted_nodes and edge.target in highlighted_nodes

            # Draw line between nodes
            self._draw_line(canvas, colors, x1, y1, x2, y2, is_highlighted)

    def _draw_line(self, canvas, colors, x1, y1, x2, y2, highlighted=False):
        """Draw a line using Bresenham's algorithm."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        color = "bright_yellow" if highlighted else "dim"
        char = "=" if highlighted else "-"

        x, y = x1, y1
        max_steps = 1000  # Prevent infinite loops

        for _ in range(max_steps):
            if 0 <= x < len(canvas[0]) and 0 <= y < len(canvas):
                if canvas[y][x] == ' ':
                    canvas[y][x] = char
                    colors[y][x] = color

            if x == x2 and y == y2:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def _draw_nodes(self, canvas, colors, screen_positions):
        """Draw nodes on the canvas."""
        if not self.graph:
            return

        # Get highlighted nodes
        highlighted_nodes = set()
        for path in self.highlighted_paths:
            highlighted_nodes.update(path)

        for node_id, (x, y) in screen_positions.items():
            node = self.graph.get_node(node_id)
            if not node:
                continue

            # Determine node symbol and color
            symbol = self._get_node_symbol(node)
            color = self._get_node_color(node, node_id in highlighted_nodes, node_id == self.selected_node)

            # Draw node
            if 0 <= x < len(canvas[0]) and 0 <= y < len(canvas):
                canvas[y][x] = symbol
                colors[y][x] = color

    def _get_node_symbol(self, node: GraphNode) -> str:
        """Get ASCII symbol for node type."""
        symbols = {
            NodeType.DOMAIN: "●",
            NodeType.SUBDOMAIN: "○",
            NodeType.URL: "□",
            NodeType.EMAIL: "@",
            NodeType.SOCIAL: "S",
            NodeType.REPOSITORY: "R",
            NodeType.IP_ADDRESS: "#",
            NodeType.TECHNOLOGY: "T",
            NodeType.CREDENTIAL: "!",
            NodeType.PATTERN: "?"
        }
        return symbols.get(node.type, "•")

    def _get_node_color(self, node: GraphNode, highlighted: bool, selected: bool) -> str:
        """Get color for node."""
        if selected:
            return "bright_cyan"
        if highlighted:
            return "bright_yellow"

        # Color by risk score
        if node.risk_score >= 70:
            return "bright_red"
        elif node.risk_score >= 40:
            return "yellow"
        elif node.type == NodeType.DOMAIN:
            return "bright_blue"
        else:
            return "green"

    def _canvas_to_text(self, canvas, colors) -> Text:
        """Convert canvas to Rich Text."""
        text = Text()

        for y, row in enumerate(canvas):
            for x, char in enumerate(row):
                color = colors[y][x] or "white"
                text.append(char, style=color)
            if y < len(canvas) - 1:
                text.append("\n")

        return text


class GraphLegend(Static):
    """Legend showing node types and controls."""

    def render(self) -> Table:
        """Render legend as a table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Symbol", style="cyan")
        table.add_column("Type")

        # Node types
        table.add_row("●", "Domain")
        table.add_row("○", "Subdomain")
        table.add_row("□", "URL")
        table.add_row("@", "Email")
        table.add_row("R", "Repository")

        return table


class GraphStats(Static):
    """Display graph statistics."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph: Optional[OSINTGraph] = None

    def set_graph(self, graph: OSINTGraph):
        """Set graph and update stats."""
        self.graph = graph
        self.refresh()

    def render(self) -> Table:
        """Render statistics table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        if self.graph:
            stats = self.graph.get_stats()
            table.add_row("Nodes", str(stats["node_count"]))
            table.add_row("Edges", str(stats["edge_count"]))
            table.add_row("Avg Degree", f"{stats['avg_degree']:.1f}")
            table.add_row("Density", f"{stats['density']:.3f}")
        else:
            table.add_row("No Data", "-")

        return table


class GraphView(Container):
    """Interactive graph visualization view."""

    def __init__(self, project_manager: ProjectManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pm = project_manager
        self.canvas = GraphCanvas()
        self.legend = GraphLegend()
        self.stats = GraphStats()

    def compose(self) -> ComposeResult:
        """Compose the graph view layout."""
        with Vertical():
            yield Label("[bold cyan]OSINT Graph Visualization[/bold cyan]")
            yield Label("[dim]Controls: +/- zoom, arrows pan, Q quit, H hierarchical, F force-directed[/dim]")
            yield self.canvas
            with Container():
                yield self.legend
                yield self.stats

    def load_graph(self, target_id: int, category: Optional[str] = None):
        """Load and display graph for a target."""
        from .graph import GraphBuilder

        try:
            target = self.pm.get_target(target_id)
            builder = GraphBuilder(self.pm)
            graph = builder.build_from_target(target, category)

            self.canvas.set_graph(graph, layout_type="force")
            self.stats.set_graph(graph)

        except Exception as e:
            self.canvas.update(Text(f"Error loading graph: {e}", style="red"))

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        if event.key == "plus" or event.key == "equals":
            self.canvas.zoom_in()
        elif event.key == "minus" or event.key == "underscore":
            self.canvas.zoom_out()
        elif event.key == "up":
            self.canvas.pan(0, 10)
        elif event.key == "down":
            self.canvas.pan(0, -10)
        elif event.key == "left":
            self.canvas.pan(10, 0)
        elif event.key == "right":
            self.canvas.pan(-10, 0)
        elif event.key == "h":
            # Switch to hierarchical layout
            if self.canvas.graph:
                self.canvas.set_graph(self.canvas.graph, layout_type="hierarchical")
        elif event.key == "f":
            # Switch to force-directed layout
            if self.canvas.graph:
                self.canvas.set_graph(self.canvas.graph, layout_type="force")
        elif event.key == "g":
            # Switch to grid layout
            if self.canvas.graph:
                self.canvas.set_graph(self.canvas.graph, layout_type="grid")
