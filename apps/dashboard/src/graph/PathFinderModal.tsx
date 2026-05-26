import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Copy, Route, Sparkles, X } from "lucide-react";
import type { GraphNode, PathPayload } from "@devgraph/schema";
import { useDashboardStore } from "../store/dashboardStore";
import { client } from "../api/client";

function rankedNodes(nodes: GraphNode[], query: string): GraphNode[] {
  if (!query.trim()) return nodes.slice(0, 30);
  const term = query.toLowerCase();
  return nodes
    .filter((n) =>
      n.qualified_name.toLowerCase().includes(term) ||
      n.name.toLowerCase().includes(term) ||
      (n.file_path ?? "").toLowerCase().includes(term),
    )
    .slice(0, 30);
}

function NodePicker({
  label,
  selected,
  query,
  onQueryChange,
  onPick,
  nodes,
}: {
  label: string;
  selected: GraphNode | null;
  query: string;
  onQueryChange: (q: string) => void;
  onPick: (node: GraphNode) => void;
  nodes: GraphNode[];
}) {
  const results = useMemo(() => rankedNodes(nodes, query), [nodes, query]);
  return (
    <div className="dg-path-picker">
      <div className="dg-path-picker-head">
        <span className="dg-path-picker-label">{label}</span>
        {selected ? (
          <span className="dg-path-picker-current" title={selected.qualified_name}>
            {selected.name}
          </span>
        ) : (
          <span className="dg-path-picker-current is-empty">choose a node…</span>
        )}
      </div>
      <input
        className="dg-path-input"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        placeholder={`Filter ${label.toLowerCase()}…`}
      />
      <div className="dg-path-results">
        {results.length === 0 ? <em>No matches.</em> : null}
        {results.map((node) => (
          <button
            key={node.id}
            className="dg-path-result"
            onClick={() => onPick(node)}
          >
            <b>{node.type}</b>
            <span className="qn">{node.qualified_name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function PathFinderModal() {
  const open = useDashboardStore((s) => s.pathFinderOpen);
  const togglePathFinder = useDashboardStore((s) => s.togglePathFinder);
  const graph = useDashboardStore((s) => s.graph);
  const selectedNodeId = useDashboardStore((s) => s.selectedNodeId);
  const nodesById = useDashboardStore((s) => s.nodesById);
  const setPathHighlight = useDashboardStore((s) => s.setPathHighlight);
  const clearPathHighlight = useDashboardStore((s) => s.clearPathHighlight);
  const selectNode = useDashboardStore((s) => s.selectNode);

  const [sourceQuery, setSourceQuery] = useState("");
  const [targetQuery, setTargetQuery] = useState("");
  const [source, setSource] = useState<GraphNode | null>(null);
  const [target, setTarget] = useState<GraphNode | null>(null);
  const [result, setResult] = useState<PathPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setError(null);
      return;
    }
    if (!source && selectedNodeId) {
      const node = nodesById.get(selectedNodeId);
      if (node) setSource(node);
    }
  }, [open, selectedNodeId, nodesById, source]);

  if (!open) return null;

  async function runFind() {
    if (!source || !target) return;
    setLoading(true);
    setError(null);
    try {
      const payload = await client.path(source.id, target.id, 12);
      setResult(payload);
      setPathHighlight(payload.nodes.map((n) => n.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Path lookup failed");
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setSource(null);
    setTarget(null);
    setSourceQuery("");
    setTargetQuery("");
    setResult(null);
    clearPathHighlight();
  }

  function close() {
    togglePathFinder();
  }

  function copyChain() {
    if (!result) return;
    const text = result.nodes.map((n) => n.qualified_name).join(" → ");
    void navigator.clipboard?.writeText(text);
  }

  return (
    <div className="dg-modal-backdrop" onClick={close}>
      <div className="dg-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="dg-modal-head">
          <div>
            <span className="eyebrow"><Route size={12} /> path finder</span>
            <h2>Trace a path through the graph</h2>
            <p className="page-subtitle">Pick a source and target. Returns the shortest undirected path and highlights it on the canvas.</p>
          </div>
          <button className="icon-button" onClick={close} aria-label="Close path finder"><X size={16} /></button>
        </div>

        <div className="dg-path-grid">
          <NodePicker
            label="Source"
            selected={source}
            query={sourceQuery}
            onQueryChange={setSourceQuery}
            onPick={setSource}
            nodes={graph.nodes}
          />
          <NodePicker
            label="Target"
            selected={target}
            query={targetQuery}
            onQueryChange={setTargetQuery}
            onPick={setTarget}
            nodes={graph.nodes}
          />
        </div>

        <div className="dg-modal-actions">
          <button className="btn btn-primary" onClick={runFind} disabled={!source || !target || loading}>
            <Sparkles size={14} /> {loading ? "finding…" : "find path"}
          </button>
          <button className="btn btn-secondary" onClick={reset}>reset</button>
          {result && result.found ? (
            <button className="btn btn-coral-soft" onClick={copyChain}>
              <Copy size={14} /> copy chain
            </button>
          ) : null}
        </div>

        {error ? <div className="alert">{error}</div> : null}

        {result ? (
          result.found ? (
            <div className="dg-path-result-list">
              <div className="head">Path · {result.nodes.length} nodes</div>
              {result.nodes.map((node, idx) => (
                <div key={node.id} className="dg-path-hop">
                  <button
                    className="dg-path-hop-node"
                    onClick={() => { selectNode(node.id); close(); }}
                    title={node.qualified_name}
                  >
                    <b>{node.type}</b>
                    <span>{node.qualified_name}</span>
                  </button>
                  {idx < result.nodes.length - 1 ? <ArrowRight size={12} className="dg-path-arrow" /> : null}
                </div>
              ))}
            </div>
          ) : (
            <div className="dg-path-empty">No path within cutoff. Try a closer target.</div>
          )
        ) : null}
      </div>
    </div>
  );
}
