import { describe, it, expect } from "vitest";
import type { GraphNode } from "@devgraph/schema";
import { buildFileTree } from "../fileTree";

function node(id: string, file_path: string | null, tier: GraphNode["confidence_tier"] = "extracted"): GraphNode {
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
    confidence_tier: tier,
    created_at: "2026-05-26T00:00:00Z",
    updated_at: "2026-05-26T00:00:00Z",
    content_hash: null,
    metadata: {},
  };
}

describe("buildFileTree", () => {
  it("builds nested directories from file paths and rolls counts upward", () => {
    const nodes = [
      node("a", "src/auth/login.py"),
      node("b", "src/auth/login.py"),
      node("c", "src/payments/checkout.py"),
    ];
    const tree = buildFileTree(nodes);
    const src = tree.children.find((c) => c.name === "src");
    expect(src).toBeDefined();
    expect(src?.isDir).toBe(true);
    expect(src?.nodeCount).toBe(3);
    const auth = src?.children.find((c) => c.name === "auth");
    expect(auth?.nodeCount).toBe(2);
  });

  it("flags changed/affected/risk via per-node options", () => {
    const nodes = [
      node("a", "src/a.py"),
      node("b", "src/b.py", "ambiguous"),
    ];
    const tree = buildFileTree(nodes, {
      changedIds: new Set(["a"]),
      affectedIds: new Set(["b"]),
    });
    expect(tree.changedCount).toBe(1);
    expect(tree.affectedCount).toBe(1);
    expect(tree.riskCount).toBe(1);
  });

  it("ignores nodes without a file_path", () => {
    const tree = buildFileTree([node("x", null)]);
    expect(tree.children).toEqual([]);
  });
});
