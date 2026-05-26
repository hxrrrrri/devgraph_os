import type { GraphNode } from "@devgraph/schema";

export interface FileTreeNode {
  name: string;
  path: string;
  isDir: boolean;
  children: FileTreeNode[];
  nodeCount: number;
  nodeIds: string[];
  changedCount: number;
  affectedCount: number;
  riskCount: number;
}

/** Build a directory tree from graph node file paths. Dirs aggregate child counts/badges. */
export function buildFileTree(
  nodes: GraphNode[],
  options: {
    changedIds?: Set<string>;
    affectedIds?: Set<string>;
  } = {},
): FileTreeNode {
  const root: FileTreeNode = {
    name: "/",
    path: "",
    isDir: true,
    children: [],
    nodeCount: 0,
    nodeIds: [],
    changedCount: 0,
    affectedCount: 0,
    riskCount: 0,
  };
  const byPath = new Map<string, FileTreeNode>();
  byPath.set("", root);

  for (const node of nodes) {
    if (!node.file_path) continue;
    const path = node.file_path.replace(/\\/g, "/");
    const segments = path.split("/").filter(Boolean);
    let parent = root;
    let acc = "";
    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      acc = acc ? `${acc}/${segment}` : segment;
      const isLeaf = i === segments.length - 1;
      let child = byPath.get(acc);
      if (!child) {
        child = {
          name: segment,
          path: acc,
          isDir: !isLeaf,
          children: [],
          nodeCount: 0,
          nodeIds: [],
          changedCount: 0,
          affectedCount: 0,
          riskCount: 0,
        };
        parent.children.push(child);
        byPath.set(acc, child);
      }
      parent = child;
    }
    parent.nodeCount += 1;
    parent.nodeIds.push(node.id);
    if (options.changedIds?.has(node.id)) parent.changedCount += 1;
    if (options.affectedIds?.has(node.id)) parent.affectedCount += 1;
    if (node.confidence_tier === "ambiguous") parent.riskCount += 1;
  }

  // Roll counts upward + sort children (dirs first, alpha).
  function rollUp(node: FileTreeNode): void {
    if (!node.isDir) return;
    for (const child of node.children) rollUp(child);
    node.nodeCount += node.children.reduce((acc, c) => acc + c.nodeCount, 0);
    node.changedCount += node.children.reduce((acc, c) => acc + c.changedCount, 0);
    node.affectedCount += node.children.reduce((acc, c) => acc + c.affectedCount, 0);
    node.riskCount += node.children.reduce((acc, c) => acc + c.riskCount, 0);
    node.children.sort((a, b) => {
      if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
  }
  rollUp(root);
  return root;
}
