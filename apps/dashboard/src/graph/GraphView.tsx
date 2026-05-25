import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { useMemo, useState } from "react";
import type { GraphPayload, GraphNode } from "@devgraph/schema";

export function GraphView({ graph }: { graph: GraphPayload }) {
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const nodes: Node[] = useMemo(
    () =>
      graph.nodes.slice(0, 150).map((node, index) => ({
        id: node.id,
        position: { x: (index % 10) * 220, y: Math.floor(index / 10) * 110 },
        data: { label: node.name },
        style: nodeStyle(node.type)
      })),
    [graph.nodes]
  );
  const edges: Edge[] = useMemo(
    () =>
      graph.edges
        .filter((edge) => nodes.some((node) => node.id === edge.source_id) && nodes.some((node) => node.id === edge.target_id))
        .slice(0, 300)
        .map((edge) => ({ id: edge.id, source: edge.source_id, target: edge.target_id, label: edge.type })),
    [graph.edges, nodes]
  );

  return (
    <section className="graph-layout">
      <div className="graph-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          onNodeClick={(_, node) => setSelected(graph.nodes.find((item) => item.id === node.id) ?? null)}
        >
          <MiniMap />
          <Controls />
          <Background />
        </ReactFlow>
      </div>
      <aside className="detail-panel">
        <h2>Node detail</h2>
        {selected ? (
          <dl>
            <dt>Name</dt>
            <dd>{selected.qualified_name}</dd>
            <dt>Type</dt>
            <dd>{selected.type}</dd>
            <dt>File</dt>
            <dd>{selected.file_path ?? "external"}</dd>
            <dt>Confidence</dt>
            <dd>{selected.confidence_tier}</dd>
          </dl>
        ) : (
          <p>Select a graph node.</p>
        )}
      </aside>
    </section>
  );
}

function nodeStyle(type: string) {
  const palette: Record<string, string> = {
    file: "#e8f1ff",
    module: "#e9f7ef",
    function: "#fff5db",
    class: "#f4edff",
    test: "#e7f8f5",
    config: "#f3f4f6",
    document: "#f7ebdf",
    api_endpoint: "#ffe8e8"
  };
  return {
    border: "1px solid #8993a0",
    borderRadius: 6,
    background: palette[type] ?? "#ffffff",
    color: "#181b20",
    minWidth: 140
  };
}

