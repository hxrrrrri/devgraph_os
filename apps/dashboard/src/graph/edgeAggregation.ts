import type { GraphEdge, GraphPayload } from "@devgraph/schema";

export interface LayerEdgeAggregation {
  sourceLayerId: string;
  targetLayerId: string;
  count: number;
  edgeTypes: string[];
}

/** Aggregate undirected layer-to-layer edge counts. Same-layer edges ignored. */
export function aggregateLayerEdges(
  graph: GraphPayload,
  nodeIdToLayerId: Map<string, string>,
): LayerEdgeAggregation[] {
  const pairs = new Map<
    string,
    { sourceLayerId: string; targetLayerId: string; count: number; edgeTypes: Set<string> }
  >();
  for (const edge of graph.edges) {
    const a = nodeIdToLayerId.get(edge.source_id);
    const b = nodeIdToLayerId.get(edge.target_id);
    if (!a || !b || a === b) continue;
    const [low, high] = a < b ? [a, b] : [b, a];
    const key = `${low}|${high}`;
    const existing = pairs.get(key);
    if (existing) {
      existing.count++;
      existing.edgeTypes.add(edge.type);
    } else {
      pairs.set(key, { sourceLayerId: low, targetLayerId: high, count: 1, edgeTypes: new Set([edge.type]) });
    }
  }
  return [...pairs.values()].map((p) => ({
    sourceLayerId: p.sourceLayerId,
    targetLayerId: p.targetLayerId,
    count: p.count,
    edgeTypes: [...p.edgeTypes],
  }));
}

export interface AggregatedContainerEdge {
  sourceContainerId: string;
  targetContainerId: string;
  count: number;
  edgeTypes: string[];
}

export interface ContainerEdgeBuckets {
  intraContainer: GraphEdge[];
  interContainerAggregated: AggregatedContainerEdge[];
}

/** Bucket edges into intra-container (preserved) and inter-container (aggregated by directed pair). */
export function aggregateContainerEdges(
  edges: GraphEdge[],
  nodeToContainer: Map<string, string>,
): ContainerEdgeBuckets {
  const intra: GraphEdge[] = [];
  const interMap = new Map<
    string,
    { sourceContainerId: string; targetContainerId: string; count: number; edgeTypes: Set<string> }
  >();
  for (const edge of edges) {
    const sc = nodeToContainer.get(edge.source_id);
    const tc = nodeToContainer.get(edge.target_id);
    if (!sc || !tc) continue;
    if (sc === tc) {
      intra.push(edge);
      continue;
    }
    const key = `${sc.length}:${sc} ${tc}`;
    const existing = interMap.get(key);
    if (existing) {
      existing.count++;
      existing.edgeTypes.add(edge.type);
    } else {
      interMap.set(key, { sourceContainerId: sc, targetContainerId: tc, count: 1, edgeTypes: new Set([edge.type]) });
    }
  }
  return {
    intraContainer: intra,
    interContainerAggregated: [...interMap.values()].map((p) => ({
      sourceContainerId: p.sourceContainerId,
      targetContainerId: p.targetContainerId,
      count: p.count,
      edgeTypes: [...p.edgeTypes],
    })),
  };
}
