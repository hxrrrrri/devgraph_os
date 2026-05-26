import dagre from "@dagrejs/dagre";
import type { Edge, Node } from "@xyflow/react";

export const NODE_WIDTH = 260;
export const NODE_HEIGHT = 110;
export const LAYER_CLUSTER_WIDTH = 320;
export const LAYER_CLUSTER_HEIGHT = 170;
export const CONTAINER_PADDING_X = 28;
export const CONTAINER_PADDING_Y = 56;

export interface LayoutOptions {
  direction?: "TB" | "LR";
  nodeSep?: number;
  rankSep?: number;
  dimensions?: Map<string, { width: number; height: number }>;
}

/** Synchronous dagre layout. Used for the architecture overview and layer-detail graphs. */
export function applyDagreLayout(
  nodes: Node[],
  edges: Edge[],
  opts: LayoutOptions = {},
): { nodes: Node[]; edges: Edge[] } {
  const direction = opts.direction ?? "TB";
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  const isLarge = nodes.length > 80;
  g.setGraph({
    rankdir: direction,
    nodesep: opts.nodeSep ?? (isLarge ? 70 : 50),
    ranksep: opts.rankSep ?? (isLarge ? 130 : 90),
    marginx: 28,
    marginy: 28,
  });
  for (const node of nodes) {
    const dims = opts.dimensions?.get(node.id);
    g.setNode(node.id, { width: dims?.width ?? NODE_WIDTH, height: dims?.height ?? NODE_HEIGHT });
  }
  for (const edge of edges) {
    g.setEdge(String(edge.source), String(edge.target));
  }
  dagre.layout(g);
  const positioned = nodes.map((node) => {
    const pos = g.node(node.id);
    if (!pos) return { ...node, position: node.position ?? { x: 0, y: 0 } };
    const dims = opts.dimensions?.get(node.id);
    const w = dims?.width ?? NODE_WIDTH;
    const h = dims?.height ?? NODE_HEIGHT;
    return { ...node, position: { x: pos.x - w / 2, y: pos.y - h / 2 } };
  });
  return { nodes: positioned, edges };
}

/**
 * Layout children inside a container box and report the resulting size.
 * Pure helper — no React Flow types required, suitable for memoization.
 */
export function layoutInsideContainer(
  childIds: string[],
  childEdges: Array<{ source: string; target: string }>,
  childDimensions?: Map<string, { width: number; height: number }>,
): {
  positions: Map<string, { x: number; y: number }>;
  size: { width: number; height: number };
} {
  if (childIds.length === 0) {
    return { positions: new Map(), size: { width: 260, height: 80 } };
  }
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 30, ranksep: 60, marginx: 12, marginy: 12 });
  for (const id of childIds) {
    const dims = childDimensions?.get(id);
    g.setNode(id, { width: dims?.width ?? NODE_WIDTH, height: dims?.height ?? NODE_HEIGHT });
  }
  for (const edge of childEdges) {
    if (childIds.includes(edge.source) && childIds.includes(edge.target)) {
      g.setEdge(edge.source, edge.target);
    }
  }
  dagre.layout(g);
  const positions = new Map<string, { x: number; y: number }>();
  let maxX = 0;
  let maxY = 0;
  for (const id of childIds) {
    const pos = g.node(id);
    if (!pos) continue;
    const dims = childDimensions?.get(id);
    const w = dims?.width ?? NODE_WIDTH;
    const h = dims?.height ?? NODE_HEIGHT;
    const x = pos.x - w / 2 + CONTAINER_PADDING_X;
    const y = pos.y - h / 2 + CONTAINER_PADDING_Y;
    positions.set(id, { x, y });
    maxX = Math.max(maxX, x + w);
    maxY = Math.max(maxY, y + h);
  }
  return {
    positions,
    size: {
      width: Math.max(280, maxX + CONTAINER_PADDING_X),
      height: Math.max(140, maxY + CONTAINER_PADDING_X),
    },
  };
}
