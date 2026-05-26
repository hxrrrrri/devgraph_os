import { describe, it, expect } from "vitest";
import type { GraphEdge, GraphNode } from "@devgraph/schema";
import { deriveContainers, buildNodeToContainer } from "../containers";

function node(id: string, file_path: string | null): GraphNode {
  return {
    id,
    type: "function",
    name: id,
    qualified_name: id,
    file_path,
    line_start: null,
    line_end: null,
    language: null,
    summary: null,
    tags: [],
    confidence: 1,
    confidence_tier: "extracted",
    created_at: "2026-05-26T00:00:00Z",
    updated_at: "2026-05-26T00:00:00Z",
    content_hash: null,
    metadata: {},
  };
}

function edge(id: string, s: string, t: string): GraphEdge {
  return {
    id,
    source_id: s,
    target_id: t,
    type: "calls",
    confidence: 1,
    confidence_tier: "extracted",
    provenance_source: "test",
    file_path: null,
    line: null,
    metadata: {},
  };
}

describe("deriveContainers", () => {
  it("groups files by first folder segment after the common prefix", () => {
    const nodes = [
      node("1", "src/auth/login.py"),
      node("2", "src/auth/logout.py"),
      node("3", "src/payments/checkout.py"),
      node("4", "src/payments/refund.py"),
    ];
    const { containers } = deriveContainers(nodes, []);
    const ids = containers.map((c) => c.id).sort();
    expect(ids).toContain("container:auth");
    expect(ids).toContain("container:payments");
  });

  it("falls back to community when one bucket dominates", () => {
    const nodes = Array.from({ length: 6 }, (_, i) => node(`n${i}`, `src/single/${i}.py`));
    nodes.push(node("alone", "src/other/alone.py"));
    const edges = nodes.slice(0, 5).map((n, i) => edge(`e${i}`, n.id, nodes[(i + 1) % 5].id));
    const { containers } = deriveContainers(nodes, edges);
    expect(containers.every((c) => c.strategy === "community")).toBe(true);
  });

  it("suppresses single-child containers when node total is above threshold", () => {
    const nodes = [
      node("1", "src/a/x.py"),
      node("2", "src/a/y.py"),
      node("3", "src/b/z.py"),
    ];
    const { containers, ungrouped } = deriveContainers(nodes, []);
    const names = containers.map((c) => c.name);
    expect(names).toContain("a");
    expect(names).not.toContain("b");
    expect(ungrouped).toContain("3");
  });

  it("returns empty for no nodes", () => {
    expect(deriveContainers([], [])).toEqual({ containers: [], ungrouped: [] });
  });
});

describe("buildNodeToContainer", () => {
  it("maps each child id back to its container", () => {
    const containers = [
      { id: "c1", name: "auth", nodeIds: ["n1", "n2"], strategy: "folder" as const },
      { id: "c2", name: "data", nodeIds: ["n3"], strategy: "folder" as const },
    ];
    const map = buildNodeToContainer(containers);
    expect(map.get("n1")).toBe("c1");
    expect(map.get("n3")).toBe("c2");
  });
});
