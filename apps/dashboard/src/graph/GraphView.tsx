import "@xyflow/react/dist/style.css";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { useMemo, useState } from "react";
import clsx from "clsx";
import type { GraphPayload, GraphNode } from "@devgraph/schema";

const palette: Record<string, string> = {
  file: "#38bdf8",
  module: "#2dd4bf",
  function: "#a3e635",
  class: "#c084fc",
  test: "#facc15",
  api_endpoint: "#fb7185",
  database_table: "#fb923c",
  config: "#f59e0b",
  document: "#93c5fd",
  section: "#60a5fa",
  resource: "#34d399"
};

export function GraphView({ graph }: { graph: GraphPayload }) {
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [enabledTypes, setEnabledTypes] = useState<Set<string>>(new Set());
  const types = useMemo(() => Array.from(new Set(graph.nodes.map((node) => node.type))).sort(), [graph.nodes]);
  const visibleNodes = useMemo(
    () => graph.nodes.filter((node) => enabledTypes.size === 0 || enabledTypes.has(node.type)).slice(0, 220),
    [enabledTypes, graph.nodes]
  );
  const nodes: Node[] = useMemo(
    () =>
      visibleNodes.map((node, index) => {
        const ring = Math.floor(index / 18);
        const angle = (index % 18) * (Math.PI / 9);
        const radius = 140 + ring * 145;
        return {
          id: node.id,
          position: { x: Math.cos(angle) * radius + 520, y: Math.sin(angle) * radius + 360 },
          data: { label: node.name.length > 28 ? `${node.name.slice(0, 25)}...` : node.name },
          style: nodeStyle(node.type)
        };
      }),
    [visibleNodes]
  );
  const ids = useMemo(() => new Set(nodes.map((node) => node.id)), [nodes]);
  const edges: Edge[] = useMemo(
    () =>
      graph.edges
        .filter((edge) => ids.has(edge.source_id) && ids.has(edge.target_id))
        .slice(0, 500)
        .map((edge) => ({
          id: edge.id,
          source: edge.source_id,
          target: edge.target_id,
          label: edge.type,
          animated: ["calls", "routes_to", "reads_from", "writes_to"].includes(edge.type),
          style: { stroke: "#2dd4bf", strokeWidth: 1.4 },
          labelStyle: { fill: "#9fb0c8", fontSize: 10 }
        })),
    [graph.edges, ids]
  );

  function toggleType(type: string) {
    setEnabledTypes((current) => {
      const next = new Set(current);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  return (
    <section className="graph-layout">
      <div className="graph-tools">
        {types.map((type) => (
          <button key={type} className={clsx(enabledTypes.has(type) && "active")} onClick={() => toggleType(type)}>
            <i style={{ background: palette[type] ?? "#64748b" }} /> {type}
          </button>
        ))}
      </div>
      <div className="graph-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          onNodeClick={(_, node) => setSelected(graph.nodes.find((item) => item.id === node.id) ?? null)}
        >
          <MiniMap nodeColor={(node) => String((node.style as { background?: string }).background ?? "#64748b")} pannable zoomable />
          <Controls />
          <Background color="#1d2a36" gap={24} />
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
            <dt>Provenance</dt>
            <dd>{String(selected.metadata.parser ?? selected.confidence_tier)}</dd>
            <dt>Source</dt>
            <dd>{selected.line_start ? `lines ${selected.line_start}-${selected.line_end ?? selected.line_start}` : "not line mapped"}</dd>
          </dl>
        ) : (
          <p>Select a graph node.</p>
        )}
      </aside>
    </section>
  );
}

function nodeStyle(type: string) {
  const color = palette[type] ?? "#64748b";
  return {
    border: `1px solid ${color}`,
    borderRadius: 8,
    background: `linear-gradient(180deg, ${color}22, #0f151d 72%)`,
    boxShadow: `0 0 28px ${color}22`,
    color: "#e8f2ff",
    minWidth: 138,
    padding: 8
  };
}
