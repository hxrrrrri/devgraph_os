import "@xyflow/react/dist/style.css";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import { useMemo } from "react";
import { useDashboardStore } from "../store/dashboardStore";
import { CustomNode, type CustomFlowNode } from "./nodes/CustomNode";
import { ContainerNode, type ContainerFlowNode } from "./nodes/ContainerNode";
import { PortalNode, type PortalFlowNode } from "./nodes/PortalNode";
import { applyDagreLayout, layoutInsideContainer, NODE_HEIGHT, NODE_WIDTH } from "./layout";
import { aggregateContainerEdges, aggregateLayerEdges } from "./edgeAggregation";
import { buildNodeToContainer, deriveContainers } from "./containers";

const NODE_TYPES = { "dg-custom": CustomNode, "dg-container": ContainerNode, "dg-portal": PortalNode };

export function LayerDetailGraph() {
  const layers = useDashboardStore((s) => s.layers);
  const activeLayerId = useDashboardStore((s) => s.activeLayerId);
  const graph = useDashboardStore((s) => s.graph);
  const nodesById = useDashboardStore((s) => s.nodesById);
  const selectedNodeId = useDashboardStore((s) => s.selectedNodeId);
  const expandedContainers = useDashboardStore((s) => s.expandedContainers);
  const changedNodeIds = useDashboardStore((s) => s.changedNodeIds);
  const affectedNodeIds = useDashboardStore((s) => s.affectedNodeIds);
  const diffMode = useDashboardStore((s) => s.diffMode);
  const pathHighlightIds = useDashboardStore((s) => s.pathHighlightIds);
  const searchQuery = useDashboardStore((s) => s.searchQuery);
  const selectNode = useDashboardStore((s) => s.selectNode);
  const toggleContainer = useDashboardStore((s) => s.toggleContainer);
  const drillIntoLayer = useDashboardStore((s) => s.drillIntoLayer);
  const nodeIdToLayerId = useDashboardStore((s) => s.nodeIdToLayerId);

  const activeLayer = useMemo(
    () => layers.find((l) => l.id === activeLayerId) ?? null,
    [layers, activeLayerId],
  );

  const layerNodes = useMemo(() => {
    if (!activeLayer) return [];
    return activeLayer.nodeIds
      .map((id) => nodesById.get(id))
      .filter((n): n is NonNullable<typeof n> => Boolean(n));
  }, [activeLayer, nodesById]);

  const layerNodeIdSet = useMemo(() => new Set(layerNodes.map((n) => n.id)), [layerNodes]);

  const layerEdges = useMemo(
    () => graph.edges.filter((e) => layerNodeIdSet.has(e.source_id) && layerNodeIdSet.has(e.target_id)),
    [graph.edges, layerNodeIdSet],
  );

  const { containers, ungrouped } = useMemo(
    () => deriveContainers(layerNodes, layerEdges),
    [layerNodes, layerEdges],
  );

  const nodeToContainer = useMemo(() => buildNodeToContainer(containers), [containers]);

  const searchHitIds = useMemo(() => {
    const term = searchQuery.trim().toLowerCase();
    if (!term) return new Set<string>();
    const set = new Set<string>();
    for (const node of layerNodes) {
      if (
        node.qualified_name.toLowerCase().includes(term) ||
        node.name.toLowerCase().includes(term) ||
        (node.file_path ?? "").toLowerCase().includes(term)
      ) {
        set.add(node.id);
      }
    }
    return set;
  }, [layerNodes, searchQuery]);

  const neighborIds = useMemo(() => {
    if (!selectedNodeId) return new Set<string>();
    const set = new Set<string>();
    for (const edge of layerEdges) {
      if (edge.source_id === selectedNodeId) set.add(edge.target_id);
      if (edge.target_id === selectedNodeId) set.add(edge.source_id);
    }
    return set;
  }, [selectedNodeId, layerEdges]);

  const flow = useMemo(() => {
    if (!activeLayer) return { nodes: [] as Node[], edges: [] as Edge[] };

    const renderedNodes: Node[] = [];
    const renderedEdges: Edge[] = [];

    const ungroupedSet = new Set(ungrouped);

    function buildCustom(nodeId: string): CustomFlowNode {
      const node = nodesById.get(nodeId)!;
      const isSelected = nodeId === selectedNodeId;
      const isHit = searchHitIds.has(nodeId);
      const isChanged = changedNodeIds.has(nodeId);
      const isAffected = affectedNodeIds.has(nodeId);
      const isFaded = diffMode && !isChanged && !isAffected;
      const isNeighbor = !isSelected && neighborIds.has(nodeId);
      const isSelectionFaded = Boolean(selectedNodeId) && !isSelected && !isNeighbor && !isHit;
      const data: CustomFlowNode["data"] = {
        node,
        isSelected,
        isSearchHighlighted: isHit,
        isDiffChanged: isChanged,
        isDiffAffected: isAffected,
        isDiffFaded: isFaded,
        isNeighbor,
        isSelectionFaded,
        isTourHighlighted: false,
        isRisky: isChanged,
        isAmbiguous: node.confidence_tier === "ambiguous",
        isOnPath: pathHighlightIds.has(nodeId),
        hasTests: false,
        hasDocs: false,
        onSelect: selectNode,
      };
      return {
        id: nodeId,
        type: "dg-custom",
        position: { x: 0, y: 0 },
        data,
      };
    }

    const containerEdgeBuckets = aggregateContainerEdges(layerEdges, nodeToContainer);

    for (const container of containers) {
      const isExpanded = expandedContainers.has(container.id);
      const hits = container.nodeIds.reduce((acc, id) => acc + (searchHitIds.has(id) ? 1 : 0), 0);
      const containerDiffAffected = container.nodeIds.some(
        (id) => changedNodeIds.has(id) || affectedNodeIds.has(id),
      );
      const containerData: ContainerFlowNode["data"] = {
        containerId: container.id,
        name: container.name,
        childCount: container.nodeIds.length,
        strategy: container.strategy,
        isExpanded,
        hasSearchHits: hits > 0,
        searchHitCount: hits,
        isDiffAffected: containerDiffAffected,
        isFocusedViaChild: selectedNodeId !== null && container.nodeIds.includes(selectedNodeId),
        onToggle: toggleContainer,
      };
      const containerNode: ContainerFlowNode = {
        id: container.id,
        type: "dg-container",
        position: { x: 0, y: 0 },
        data: containerData,
        width: 320,
        height: 80,
      };
      if (isExpanded) {
        const childIds = container.nodeIds;
        const childEdges = layerEdges
          .filter((e) => childIds.includes(e.source_id) && childIds.includes(e.target_id))
          .map((e) => ({ source: e.source_id, target: e.target_id }));
        const { positions, size } = layoutInsideContainer(childIds, childEdges);
        containerNode.width = size.width;
        containerNode.height = size.height;
        renderedNodes.push(containerNode);
        for (const childId of childIds) {
          const child = buildCustom(childId);
          const pos = positions.get(childId) ?? { x: 0, y: 0 };
          renderedNodes.push({ ...child, parentId: container.id, extent: "parent", position: pos });
        }
      } else {
        renderedNodes.push(containerNode);
      }
    }

    for (const id of ungroupedSet) renderedNodes.push(buildCustom(id));

    // Intra-container edges (visible only when both endpoints are expanded children)
    for (const edge of containerEdgeBuckets.intraContainer) {
      const containerId = nodeToContainer.get(edge.source_id);
      if (!containerId || !expandedContainers.has(containerId)) continue;
      renderedEdges.push({
        id: edge.id,
        source: edge.source_id,
        target: edge.target_id,
        label: edge.type,
        style: { stroke: "rgba(124, 215, 196, 0.55)", strokeWidth: 1.1 },
        labelStyle: { fill: "var(--muted-dark)", fontSize: 9, fontFamily: "var(--font-mono)" },
        labelBgStyle: { fill: "rgba(33, 31, 27, 0.85)" },
      });
    }

    // Inter-container aggregated edges
    for (const agg of containerEdgeBuckets.interContainerAggregated) {
      const sourceVisible = renderedNodes.some((n) => n.id === agg.sourceContainerId);
      const targetVisible = renderedNodes.some((n) => n.id === agg.targetContainerId);
      if (!sourceVisible || !targetVisible) continue;
      renderedEdges.push({
        id: `agg:${agg.sourceContainerId}->${agg.targetContainerId}`,
        source: agg.sourceContainerId,
        target: agg.targetContainerId,
        label: `${agg.count}`,
        style: {
          stroke: "rgba(255, 181, 157, 0.45)",
          strokeWidth: Math.min(4, 1 + Math.log2(agg.count + 1)),
        },
        labelStyle: { fill: "var(--muted-dark)", fontSize: 10, fontFamily: "var(--font-mono)" },
        labelBgStyle: { fill: "rgba(33, 31, 27, 0.85)" },
      });
    }

    // Portals: cross-layer connections, rendered as their own nodes at the
    // edge of the canvas. Click a portal to drill into the target layer.
    const layerAggs = aggregateLayerEdges(graph, nodeIdToLayerId);
    const layerNameById = new Map(layers.map((l) => [l.id, l.name] as const));
    const layerColorById = new Map(layers.map((l) => [l.id, l.color] as const));
    for (const agg of layerAggs) {
      if (agg.sourceLayerId !== activeLayer.id && agg.targetLayerId !== activeLayer.id) continue;
      const other = agg.sourceLayerId === activeLayer.id ? agg.targetLayerId : agg.sourceLayerId;
      const portalId = `portal:${other}`;
      const portalData: PortalFlowNode["data"] = {
        targetLayerId: other,
        targetLayerName: layerNameById.get(other) ?? other,
        connectionCount: agg.count,
        color: layerColorById.get(other) ?? "var(--muted-dark)",
        onTravel: drillIntoLayer,
      };
      renderedNodes.push({
        id: portalId,
        type: "dg-portal",
        position: { x: 0, y: 0 },
        data: portalData,
      });
      // Connect first visible container to the portal so dagre lays it out near the edge.
      const anchor = renderedNodes.find(
        (n) => n.type === "dg-container" || n.type === "dg-custom",
      );
      if (anchor) {
        renderedEdges.push({
          id: `portal-edge:${other}`,
          source: anchor.id,
          target: portalId,
          label: `${agg.count}`,
          style: {
            stroke: "rgba(212, 187, 255, 0.45)",
            strokeWidth: 1,
            strokeDasharray: "4 4",
          },
          labelStyle: { fill: "var(--muted-dark)", fontSize: 10, fontFamily: "var(--font-mono)" },
          labelBgStyle: { fill: "rgba(33, 31, 27, 0.85)" },
        });
      }
    }

    // Outer layout: only top-level (non-child) nodes get dagre positions.
    const topLevel = renderedNodes.filter((n) => !("parentId" in n) || !n.parentId);
    const dims = new Map<string, { width: number; height: number }>();
    for (const n of topLevel) dims.set(n.id, { width: n.width ?? NODE_WIDTH, height: n.height ?? NODE_HEIGHT });
    const topEdges = renderedEdges.filter(
      (e) => topLevel.some((n) => n.id === e.source) && topLevel.some((n) => n.id === e.target),
    );
    const laid = applyDagreLayout(topLevel, topEdges, { direction: "TB", dimensions: dims });
    const posById = new Map(laid.nodes.map((n) => [n.id, n.position]));
    const positionedTop = topLevel.map((n) => ({ ...n, position: posById.get(n.id) ?? { x: 0, y: 0 } }));
    const positionedChildren = renderedNodes.filter((n) => "parentId" in n && n.parentId);
    return { nodes: [...positionedTop, ...positionedChildren], edges: renderedEdges };
  }, [
    activeLayer,
    nodesById,
    selectedNodeId,
    searchHitIds,
    changedNodeIds,
    affectedNodeIds,
    diffMode,
    neighborIds,
    selectNode,
    layerEdges,
    containers,
    ungrouped,
    nodeToContainer,
    expandedContainers,
    toggleContainer,
    pathHighlightIds,
    layers,
    nodeIdToLayerId,
    drillIntoLayer,
    graph,
  ]);

  if (!activeLayer) {
    return (
      <div className="graph-empty">
        <h3>Select a layer</h3>
        <p>Return to the overview and click a layer cluster.</p>
      </div>
    );
  }

  return (
    <div className="graph-canvas">
      <ReactFlow
        nodes={flow.nodes}
        edges={flow.edges}
        nodeTypes={NODE_TYPES}
        fitView
        minZoom={0.2}
        maxZoom={1.5}
        onNodeClick={(_, node) => {
          if (node.type === "dg-custom") selectNode(node.id);
        }}
        onPaneClick={() => selectNode(null)}
        proOptions={{ hideAttribution: true }}
      >
        <MiniMap pannable zoomable maskColor="rgba(14, 13, 11, 0.7)" />
        <Controls showInteractive={false} />
        <Background color="rgba(124, 215, 196, 0.10)" gap={28} />
      </ReactFlow>
    </div>
  );
}
