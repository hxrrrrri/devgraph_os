import "@xyflow/react/dist/style.css";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { useMemo } from "react";
import { useDashboardStore } from "../store/dashboardStore";
import { LayerClusterNode, type LayerClusterFlowNode } from "./nodes/LayerClusterNode";
import { applyDagreLayout, LAYER_CLUSTER_HEIGHT, LAYER_CLUSTER_WIDTH } from "./layout";
import { aggregateLayerEdges } from "./edgeAggregation";
import { computeLayerStats } from "./layerStats";

const NODE_TYPES = { "dg-layer-cluster": LayerClusterNode };

export function ArchitectureOverview() {
  const layers = useDashboardStore((s) => s.layers);
  const graph = useDashboardStore((s) => s.graph);
  const nodesById = useDashboardStore((s) => s.nodesById);
  const nodeIdToLayerId = useDashboardStore((s) => s.nodeIdToLayerId);
  const changedNodeIds = useDashboardStore((s) => s.changedNodeIds);
  const affectedNodeIds = useDashboardStore((s) => s.affectedNodeIds);
  const searchQuery = useDashboardStore((s) => s.searchQuery);
  const drillIntoLayer = useDashboardStore((s) => s.drillIntoLayer);

  const searchMatchIds = useMemo(() => {
    const term = searchQuery.trim().toLowerCase();
    if (!term) return new Set<string>();
    const set = new Set<string>();
    for (const node of graph.nodes) {
      if (
        node.qualified_name.toLowerCase().includes(term) ||
        node.name.toLowerCase().includes(term) ||
        (node.file_path ?? "").toLowerCase().includes(term)
      ) {
        set.add(node.id);
      }
    }
    return set;
  }, [graph.nodes, searchQuery]);

  const flowNodes: LayerClusterFlowNode[] = useMemo(() => {
    return layers.map((layer) => {
      const stats = computeLayerStats(layer, nodesById, {
        changedIds: changedNodeIds,
        affectedIds: affectedNodeIds,
        searchMatchIds,
      });
      const data: LayerClusterFlowNode["data"] = {
        layerId: layer.id,
        name: layer.name,
        description: layer.description,
        color: layer.color,
        fileCount: layer.stats.files,
        symbolCount: layer.stats.symbols,
        testCount: layer.stats.tests,
        docCount: layer.stats.docs,
        changedCount: stats.changedCount,
        affectedCount: stats.affectedCount,
        searchMatchCount: stats.searchMatchCount,
        riskLevel: stats.riskLevel,
        onDrillIn: drillIntoLayer,
      };
      const node: LayerClusterFlowNode = {
        id: layer.id,
        type: "dg-layer-cluster",
        position: { x: 0, y: 0 },
        data,
        width: LAYER_CLUSTER_WIDTH,
        height: LAYER_CLUSTER_HEIGHT,
      };
      return node;
    });
  }, [layers, nodesById, changedNodeIds, affectedNodeIds, searchMatchIds, drillIntoLayer]);

  const flowEdges: Edge[] = useMemo(() => {
    const aggregated = aggregateLayerEdges(graph, nodeIdToLayerId);
    return aggregated.map((agg) => ({
      id: `${agg.sourceLayerId}->${agg.targetLayerId}`,
      source: agg.sourceLayerId,
      target: agg.targetLayerId,
      label: `${agg.count}`,
      animated: false,
      style: {
        stroke: "rgba(255, 181, 157, 0.45)",
        strokeWidth: Math.min(4, 1 + Math.log2(agg.count + 1)),
      },
      labelStyle: { fill: "var(--muted-dark)", fontSize: 10, fontFamily: "var(--font-mono)" },
      labelBgStyle: { fill: "rgba(33, 31, 27, 0.85)" },
    }));
  }, [graph, nodeIdToLayerId]);

  const laidOut = useMemo(() => {
    const dims = new Map<string, { width: number; height: number }>();
    for (const node of flowNodes) dims.set(node.id, { width: LAYER_CLUSTER_WIDTH, height: LAYER_CLUSTER_HEIGHT });
    return applyDagreLayout(flowNodes, flowEdges, { direction: "TB", dimensions: dims, nodeSep: 60, rankSep: 110 });
  }, [flowNodes, flowEdges]);

  if (layers.length === 0) {
    return (
      <div className="graph-empty">
        <h3>No graph yet</h3>
        <p>Build it first.</p>
        <code>devgraph build</code>
      </div>
    );
  }

  return (
    <div className="graph-canvas">
      <ReactFlow
        nodes={laidOut.nodes}
        edges={laidOut.edges}
        nodeTypes={NODE_TYPES}
        fitView
        minZoom={0.2}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <MiniMap
          nodeColor={(n) => String((n.data as { color?: string } | undefined)?.color ?? "var(--muted-dark)")}
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
