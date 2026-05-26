import { describe, it, expect } from "vitest";
import type { GraphEdge, GraphPayload } from "@devgraph/schema";
import { aggregateContainerEdges, aggregateLayerEdges } from "../edgeAggregation";

function edge(id: string, s: string, t: string, type: GraphEdge["type"] = "calls"): GraphEdge {
  return {
    id, source_id: s, target_id: t, type,
    confidence: 1, confidence_tier: "extracted", provenance_source: "test",
    file_path: null, line: null, metadata: {},
  };
}

describe("aggregateLayerEdges", () => {
  it("collapses A->B and B->A into one canonical pair", () => {
    const payload: GraphPayload = {
      nodes: [],
      edges: [edge("e1", "a", "b"), edge("e2", "b", "a"), edge("e3", "a", "a")],
    };
    const layerMap = new Map([["a", "L1"], ["b", "L2"]]);
    const aggs = aggregateLayerEdges(payload, layerMap);
    expect(aggs).toHaveLength(1);
    expect(aggs[0].count).toBe(2);
    expect(aggs[0].edgeTypes).toContain("calls");
  });
  it("ignores edges where either endpoint has no layer assignment", () => {
    const payload: GraphPayload = { nodes: [], edges: [edge("e1", "a", "z")] };
    const layerMap = new Map([["a", "L1"]]);
    expect(aggregateLayerEdges(payload, layerMap)).toEqual([]);
  });
});

describe("aggregateContainerEdges", () => {
  it("buckets intra and inter container edges", () => {
    const edges = [
      edge("e1", "n1", "n2"),
      edge("e2", "n1", "n3"),
      edge("e3", "n3", "n4", "imports"),
    ];
    const map = new Map([
      ["n1", "c1"],
      ["n2", "c1"],
      ["n3", "c2"],
      ["n4", "c2"],
    ]);
    const buckets = aggregateContainerEdges(edges, map);
    expect(buckets.intraContainer).toHaveLength(2);
    expect(buckets.interContainerAggregated).toHaveLength(1);
    expect(buckets.interContainerAggregated[0].sourceContainerId).toBe("c1");
    expect(buckets.interContainerAggregated[0].targetContainerId).toBe("c2");
  });
});
