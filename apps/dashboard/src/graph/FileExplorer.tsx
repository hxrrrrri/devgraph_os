import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, FileCode2, Folder, FolderOpen, Search, X } from "lucide-react";
import clsx from "clsx";
import { useDashboardStore } from "../store/dashboardStore";
import { buildFileTree, type FileTreeNode } from "./fileTree";

function rowMatches(node: FileTreeNode, term: string): boolean {
  if (!term) return true;
  if (node.path.toLowerCase().includes(term)) return true;
  return node.children.some((child) => rowMatches(child, term));
}

function TreeRow({
  node,
  depth,
  expanded,
  toggle,
  onPick,
  query,
  activePath,
}: {
  node: FileTreeNode;
  depth: number;
  expanded: Set<string>;
  toggle: (path: string) => void;
  onPick: (node: FileTreeNode) => void;
  query: string;
  activePath: string | null;
}) {
  const isOpen = expanded.has(node.path) || (query && rowMatches(node, query));
  const Icon = node.isDir ? (isOpen ? FolderOpen : Folder) : FileCode2;
  const Caret = isOpen ? ChevronDown : ChevronRight;

  return (
    <>
      <button
        className={clsx(
          "dg-file-row",
          node.isDir && "is-dir",
          activePath === node.path && "is-active",
        )}
        style={{ paddingLeft: 8 + depth * 12 }}
        onClick={() => {
          if (node.isDir) toggle(node.path);
          else onPick(node);
        }}
      >
        {node.isDir ? <Caret size={11} className="dg-file-caret" /> : <span style={{ width: 11 }} />}
        <Icon size={12} className="dg-file-icon" />
        <span className="dg-file-name">{node.name}</span>
        <span className="dg-file-meta">
          {node.nodeCount}
          {node.changedCount > 0 ? <span className="dg-file-badge changed">{node.changedCount}</span> : null}
          {node.affectedCount > 0 ? <span className="dg-file-badge affected">{node.affectedCount}</span> : null}
          {node.riskCount > 0 ? <span className="dg-file-badge risk">{node.riskCount}</span> : null}
        </span>
      </button>
      {node.isDir && isOpen
        ? node.children
            .filter((c) => rowMatches(c, query))
            .map((c) => (
              <TreeRow
                key={c.path}
                node={c}
                depth={depth + 1}
                expanded={expanded}
                toggle={toggle}
                onPick={onPick}
                query={query}
                activePath={activePath}
              />
            ))
        : null}
    </>
  );
}

export function FileExplorer() {
  const open = useDashboardStore((s) => s.fileExplorerOpen);
  const toggleFileExplorer = useDashboardStore((s) => s.toggleFileExplorer);
  const graph = useDashboardStore((s) => s.graph);
  const changedNodeIds = useDashboardStore((s) => s.changedNodeIds);
  const affectedNodeIds = useDashboardStore((s) => s.affectedNodeIds);
  const openCodeViewer = useDashboardStore((s) => s.openCodeViewer);
  const selectNode = useDashboardStore((s) => s.selectNode);

  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [activePath, setActivePath] = useState<string | null>(null);

  const tree = useMemo(
    () => buildFileTree(graph.nodes, { changedIds: changedNodeIds, affectedIds: affectedNodeIds }),
    [graph.nodes, changedNodeIds, affectedNodeIds],
  );

  if (!open) return null;

  function toggle(path: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  function onPick(node: FileTreeNode) {
    setActivePath(node.path);
    if (node.nodeIds.length > 0) {
      selectNode(node.nodeIds[0]);
      openCodeViewer(node.nodeIds[0]);
    }
  }

  return (
    <aside className="dg-file-explorer">
      <header className="dg-file-explorer-head">
        <span className="eyebrow"><Folder size={12} /> files</span>
        <button className="icon-button" onClick={toggleFileExplorer} aria-label="Close file explorer">
          <X size={14} />
        </button>
      </header>
      <label className="search dg-file-search">
        <Search size={12} />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="filter files…" />
      </label>
      <div className="dg-file-tree">
        {tree.children.length === 0 ? (
          <em>No files indexed.</em>
        ) : (
          tree.children
            .filter((c) => rowMatches(c, query.toLowerCase()))
            .map((c) => (
              <TreeRow
                key={c.path}
                node={c}
                depth={0}
                expanded={expanded}
                toggle={toggle}
                onPick={onPick}
                query={query.toLowerCase()}
                activePath={activePath}
              />
            ))
        )}
      </div>
    </aside>
  );
}
