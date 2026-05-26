import "@xyflow/react/dist/style.css";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { useMemo } from "react";
import type { GraphEdge, GraphNode } from "@devgraph/schema";
import { useDashboardStore, type GraphMode } from "../store/dashboardStore";
import { CustomNode, type CustomFlowNode } from "./nodes/CustomNode";
import { applyDagreLayout } from "./layout";
import { detectCommunities } from "./louvain";

const NODE_TYPES = { "dg-custom": CustomNode };

const FLOW_EDGE_TYPES = new Set(["calls", "routes_to", "reads_from", "writes_to", "depends_on"]);

function neighborhood(seed: Set<string>, edges: GraphEdge[], depth: number): Set<string> {
  let frontier = new Set(seed);
  const visited = new Set(seed);
  for (let i = 0; i < depth; i++) {
    const next = new Set<string>();
    for (const edge of edges) {
      if (frontier.has(edge.source_id) && !visited.has(edge.target_id)) {
        next.add(edge.target_id);
        visited.add(edge.target_id);
      }
      if (frontier.has(edge.target_id) && !visited.has(edge.source_id)) {
        next.add(edge.source_id);
        visited.add(edge.source_id);
      }
    }
    if (next.size === 0) break;
    frontier = next;
  }
  return visited;
}

function pickNodes(
  mode: GraphMode,
  graph: { nodes: GraphNode[]; edges: GraphEdge[] },
  changed: Set<string>,
  affected: Set<string>,
): { nodeIds: Set<string>; direction: "TB" | "LR" } {
  if (mode === "Impact") {
    const seed = new Set<string>([...changed, ...affected]);
    if (seed.size === 0) return { nodeIds: new Set(), direction: "TB" };
    return { nodeIds: neighborhood(seed, graph.edges, 1), direction: "TB" };
  }
  if (mode === "Flow") {
    const ids = new Set<string>();
    for (const edge of graph.edges) {
      if (!FLOW_EDGE_TYPES.has(edge.type)) continue;
      ids.add(edge.source_id);
      ids.add(edge.target_id);
    }
    return { nodeIds: ids, direction: "LR" };
  }
  if (mode === "Community") {
    return { nodeIds: new Set(graph.nodes.map((n) => n.id)), direction: "TB" };
  }
  return { nodeIds: new Set(graph.nodes.map((n) => n.id)), direction: "TB" };
}

export function ModeGraph({ mode }: { mode: GraphMode }) {
  const graph = useDashboardStore((s) => s.graph);
  const nodesById = useDashboardStore((s) => s.nodesById);
  const changed = useDashboardStore((s) => s.changedNodeIds);
  const affected = useDashboardStore((s) => s.affectedNodeIds);
  const selectedNodeId = useDashboardStore((s) => s.selectedNodeId);
  const pathHighlightIds = useDashboardStore((s) => s.pathHighlightIds);
  const selectNode = useDashboardStore((s) => s.selectNode);

  const picked = useMemo(() => pickNodes(mode, graph, changed, affected), [mode, graph, changed, affected]);

  const filteredEdges = useMemo(() => {
    if (mode === "Flow") {
      return graph.edges.filter(
        (e) => FLOW_EDGE_TYPES.has(e.type) && picked.nodeIds.has(e.source_id) && picked.nodeIds.has(e.target_id),
      );
    }
    return graph.edges.filter(
      (e) => picked.nodeIds.has(e.source_id) && picked.nodeIds.has(e.target_id),
    );
  }, [graph.edges, picked, mode]);

  const visibleNodeList = useMemo(
    () => [...picked.nodeIds].map((id) => nodesById.get(id)).filter((n): n is GraphNode => Boolean(n)),
    [picked, nodesById],
  );

  const communityIndex = useMemo(() => {
    if (mode !== "Community") return new Map<string, number>();
    return detectCommunities(visibleNodeList.map((n) => n.id), filteredEdges);
  }, [mode, visibleNodeList, filteredEdges]);

  const flowNodes: CustomFlowNode[] = useMemo(() => {
    return visibleNodeList.slice(0, 240).map((node) => {
      const isSelected = node.id === selectedNodeId;
      const data: CustomFlowNode["data"] = {
        node,
        isSelected,
        isSearchHighlighted: false,
        isDiffChanged: changed.has(node.id),
        isDiffAffected: affected.has(node.id),
        isDiffFaded: false,
        isNeighbor: false,
        isSelectionFaded: false,
        isTourHighlighted: false,
        isRisky: changed.has(node.id),
        isAmbiguous: node.confidence_tier === "ambiguous",
        isOnPath: pathHighlightIds.has(node.id),
        hasTests: false,
        hasDocs: false,
        onSelect: selectNode,
      };
      return {
        id: node.id,
        type: "dg-custom",
        position: { x: 0, y: 0 },
        data,
      };
    });
  }, [visibleNodeList, selectedNodeId, changed, affected, pathHighlightIds, selectNode]);

  const flowEdges: Edge[] = useMemo(
    () =>
      filteredEdges.slice(0, 500).map((edge) => ({
        id: edge.id,
        source: edge.source_id,
        target: edge.target_id,
        label: edge.type,
        animated: mode === "Flow",
        style: { stroke: "rgba(124, 215, 196, 0.45)", strokeWidth: 1.1 },
        labelStyle: { fill: "var(--muted-dark)", fontSize: 10, fontFamily: "var(--font-mono)" },
        labelBgStyle: { fill: "rgba(33, 31, 27, 0.85)" },
      })),
    [filteredEdges, mode],
  );

  const layout = useMemo(() => applyDagreLayout(flowNodes as Node[], flowEdges, { direction: picked.direction }), [flowNodes, flowEdges, picked.direction]);

  if (flowNodes.length === 0) {
    return (
      <div className="graph-empty">
        <h3>No {mode.toLowerCase()} data</h3>
        <p>
          {mode === "Impact" ? "Run a review first to populate changed/affected nodes."
            : mode === "Flow" ? "No call / route / read / write edges found in the current graph."
            : "Graph is empty — build it first."}
        </p>
      </div>
    );
  }

  return (
    <div className="graph-canvas">
      <ReactFlow
        nodes={layout.nodes}
        edges={layout.edges}
        nodeTypes={NODE_TYPES}
        fitView
        minZoom={0.2}
        maxZoom={1.5}
        onNodeClick={(_, node) => selectNode(node.id)}
        onPaneClick={() => selectNode(null)}
        proOptions={{ hideAttribution: true }}
      >
        <MiniMap
          nodeColor={(n) => {
            const id = n.id;
            if (mode === "Community") {
              const community = communityIndex.get(id) ?? 0;
              const palette = ["#FFB59D", "#7CD7C4", "#D4BBFF", "#E8A55A", "#5DB872"];
              return palette[community % palette.length];
            }
            if (changed.has(id)) return "var(--primary-coral-bright)";
            if (affected.has(id)) return "var(--accent-teal)";
            return "var(--muted-dark)";
          }}
          pannable
          zoomable
          maskColor="rgba(14, 13, 11, 0.7)"
        />
        <Controls showInteractive={false} />
        <Background color="rgba(124, 215, 196, 0.10)" gap={28} />
      </ReactFlow>
    </div>
  );
}
