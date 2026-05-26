import { describe, it, expect } from "vitest";
import type { GraphNode } from "@devgraph/schema";
import type { DerivedLayer } from "../../store/dashboardStore";
import { computeLayerStats } from "../layerStats";

function node(id: string, tier: GraphNode["confidence_tier"] = "extracted"): GraphNode {
  return {
    id,
    type: "function",
    name: id,
    qualified_name: id,
    file_path: null,
    line_start: null,
    line_end: null,
    language: null,
    summary: null,
    tags: [],
    confidence: 1,
    confidence_tier: tier,
    created_at: "2026-05-26T00:00:00Z",
    updated_at: "2026-05-26T00:00:00Z",
    content_hash: null,
    metadata: {},
  };
}

describe("computeLayerStats", () => {
  const layer: DerivedLayer = {
    id: "app",
    name: "App",
    description: "",
    color: "#fff",
    nodeIds: ["a", "b", "c"],
    stats: { files: 0, symbols: 3, tests: 0, docs: 0 },
  };
  const nodesById = new Map([
    ["a", node("a")],
    ["b", node("b", "ambiguous")],
    ["c", node("c")],
  ]);

  it("counts changed/affected/match buckets", () => {
    const stats = computeLayerStats(layer, nodesById, {
      changedIds: new Set(["a"]),
      affectedIds: new Set(["b"]),
      searchMatchIds: new Set(["c"]),
    });
    expect(stats.changedCount).toBe(1);
    expect(stats.affectedCount).toBe(1);
    expect(stats.searchMatchCount).toBe(1);
    expect(stats.resolvedCount).toBe(3);
  });

  it("escalates risk when ambiguous ratio rises", () => {
    const flaky: DerivedLayer = { ...layer, nodeIds: ["b", "b2"] };
    const flakyMap = new Map([
      ["b", node("b", "ambiguous")],
      ["b2", node("b2", "ambiguous")],
    ]);
    const stats = computeLayerStats(flaky, flakyMap, {});
    expect(stats.riskLevel).toBe("high");
  });
});
