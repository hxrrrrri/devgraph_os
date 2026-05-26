import Graph from "graphology";
import louvain from "graphology-communities-louvain";
import type { GraphEdge } from "@devgraph/schema";

/**
 * Deterministic community detection on an unweighted, undirected projection.
 * Returns a Map<nodeId, communityIndex>. Isolated nodes still receive an id.
 */
export function detectCommunities(
  nodeIds: string[],
  edges: Pick<GraphEdge, "source_id" | "target_id">[],
): Map<string, number> {
  if (nodeIds.length === 0) return new Map();
  const graph = new Graph({ type: "undirected", allowSelfLoops: false, multi: false });
  for (const id of nodeIds) graph.addNode(id);
  const idSet = new Set(nodeIds);
  for (const edge of edges) {
    if (!idSet.has(edge.source_id) || !idSet.has(edge.target_id)) continue;
    if (edge.source_id === edge.target_id) continue;
    if (graph.hasEdge(edge.source_id, edge.target_id)) continue;
    graph.addEdge(edge.source_id, edge.target_id);
  }
  if (graph.size === 0) {
    const map = new Map<string, number>();
    nodeIds.forEach((id, idx) => map.set(id, idx));
    return map;
  }
  const assignment = louvain(graph, { randomWalk: false }) as Record<string, number>;
  const result = new Map<string, number>();
  for (const id of nodeIds) {
    result.set(id, assignment[id] ?? 0);
  }
  return result;
}
