import { describe, it, expect } from "vitest";
import type { GraphEdge, GraphNode } from "@devgraph/schema";
import { classifyNode, deriveArchitecture, mapReviewToLayers } from "../graphAdapter";

function node(partial: Partial<GraphNode> & { id: string; type: GraphNode["type"]; name: string }): GraphNode {
  return {
    id: partial.id,
    type: partial.type,
    name: partial.name,
    qualified_name: partial.qualified_name ?? partial.name,
    file_path: partial.file_path ?? null,
    line_start: null,
    line_end: null,
    language: partial.language ?? null,
    summary: null,
    tags: [],
    confidence: 1,
    confidence_tier: partial.confidence_tier ?? "extracted",
    created_at: "2026-05-26T00:00:00Z",
    updated_at: "2026-05-26T00:00:00Z",
    content_hash: null,
    metadata: partial.metadata ?? {},
  };
}

function edge(id: string, source: string, target: string, type: GraphEdge["type"] = "calls"): GraphEdge {
  return {
    id,
    source_id: source,
    target_id: target,
    type,
    confidence: 1,
    confidence_tier: "extracted",
    provenance_source: "test",
    file_path: null,
    line: null,
    metadata: {},
  };
}

describe("classifyNode", () => {
  it("buckets tests by node type even when path is ambiguous", () => {
    expect(classifyNode(node({ id: "1", type: "test", name: "t" }))).toBe("tests");
  });
  it("buckets entry by framework route metadata", () => {
    expect(
      classifyNode(node({ id: "2", type: "function", name: "f", metadata: { is_route: true } })),
    ).toBe("entry");
  });
  it("buckets data by path", () => {
    expect(
      classifyNode(node({ id: "3", type: "module", name: "m", file_path: "src/db/users.py" })),
    ).toBe("data");
  });
  it("buckets ui by tsx language", () => {
    expect(
      classifyNode(node({ id: "4", type: "module", name: "m", language: "tsx" })),
    ).toBe("ui");
  });
  it("falls back to app for symbols without strong signal", () => {
    expect(classifyNode(node({ id: "5", type: "class", name: "C" }))).toBe("app");
  });
});

describe("deriveArchitecture", () => {
  it("partitions nodes and ranks top connected", () => {
    const nodes = [
      node({ id: "a", type: "function", name: "a", file_path: "src/app/a.py" }),
      node({ id: "b", type: "function", name: "b", file_path: "src/db/b.py" }),
      node({ id: "t", type: "test", name: "t" }),
    ];
    const edges = [edge("e1", "a", "b"), edge("e2", "b", "a")];
    const result = deriveArchitecture({ nodes, edges });
    const ids = result.layers.map((l) => l.id);
    expect(ids).toContain("app");
    expect(ids).toContain("data");
    expect(ids).toContain("tests");
    expect(result.topConnected[0].id).toMatch(/^[ab]$/);
    expect(result.nodeIdToLayerId.get("a")).toBe("app");
    expect(result.nodeIdToLayerId.get("b")).toBe("data");
  });

  it("returns empty when graph has no nodes", () => {
    const result = deriveArchitecture({ nodes: [], edges: [] });
    expect(result.layers).toEqual([]);
    expect(result.topConnected).toEqual([]);
  });
});

describe("mapReviewToLayers", () => {
  it("counts changed and affected ids per layer", () => {
    const nodeIdToLayerId = new Map<string, string>([
      ["a", "app"],
      ["b", "data"],
    ]);
    const result = mapReviewToLayers(["a"], ["b", "a"], nodeIdToLayerId);
    expect(result.changedByLayer.get("app")).toBe(1);
    expect(result.affectedByLayer.get("app")).toBe(1);
    expect(result.affectedByLayer.get("data")).toBe(1);
  });
});
