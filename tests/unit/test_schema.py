from devgraph.core.ids import node_id
from devgraph.core.schema import Edge, Node


def test_node_and_edge_schema_validation() -> None:
    node = Node(
        id=node_id("function", "src/auth.py::login"),
        type="function",
        name="login",
        qualified_name="src/auth.py::login",
        file_path="src/auth.py",
        line_start=1,
        line_end=3,
        language="python",
        content_hash="abc",
    )
    edge = Edge(
        id="edge:test",
        source_id=node.id,
        target_id=node.id,
        type="calls",
        provenance_source="test",
    )
    assert node.confidence_tier == "extracted"
    assert edge.confidence == 1.0

