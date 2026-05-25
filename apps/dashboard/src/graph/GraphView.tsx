import "@xyflow/react/dist/style.css";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import { client } from "../api/client";
import type { Community } from "@devgraph/schema";
import { motion } from "framer-motion";
import clsx from "clsx";
import {
  ArrowRight,
  Code2,
  Copy,
  ExternalLink,
  FileCode,
  GitBranch,
  Layers,
  Network,
  Sparkles,
  X
} from "lucide-react";
import type { GraphPayload, GraphNode } from "@devgraph/schema";

const palette: Record<string, string> = {
  file: "#FFB59D",
  module: "#7CD7C4",
  function: "#D4BBFF",
  class: "#D4BBFF",
  test: "#E8A55A",
  api_endpoint: "#FFB59D",
  database_table: "#E8A55A",
  config: "#E8A55A",
  document: "#7CD7C4",
  section: "#7CD7C4",
  resource: "#7CD7C4"
};

const MODES = ["Overview", "Impact", "Architecture", "Flow", "Community"] as const;
type Mode = (typeof MODES)[number];

const COMMON_TYPES = ["file", "function", "class", "module", "test", "api_endpoint", "database_table", "config"];

export function GraphView({ graph }: { graph: GraphPayload }) {
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [enabledTypes, setEnabledTypes] = useState<Set<string>>(new Set());
  const [mode, setMode] = useState<Mode>("Overview");
  const [communities, setCommunities] = useState<Community[]>([]);

  useEffect(() => {
    if (mode !== "Community" || communities.length) return;
    let cancelled = false;
    client.communities().then((payload) => {
      if (!cancelled) setCommunities(payload.communities);
    }).catch(() => { /* keep empty array; legend handles it */ });
    return () => { cancelled = true; };
  }, [mode, communities.length]);

  const allTypes = useMemo(() => {
    const fromGraph = Array.from(new Set(graph.nodes.map((node) => node.type))).sort();
    return Array.from(new Set([...COMMON_TYPES, ...fromGraph]));
  }, [graph.nodes]);

  const communityIndex = useMemo(() => {
    const map = new Map<string, number>();
    communities.forEach((community, idx) => map.set(community.name, idx));
    return map;
  }, [communities]);

  const visibleNodes = useMemo(() => {
    const filtered = graph.nodes.filter((node) => enabledTypes.size === 0 || enabledTypes.has(node.type));
    if (mode === "Impact") {
      return filtered.filter((node) => /auth|payment|api|service|router|gateway/i.test(node.qualified_name)).slice(0, 200);
    }
    if (mode === "Architecture") {
      return filtered.filter((node) => ["module", "class", "api_endpoint", "database_table", "service"].includes(node.type)).slice(0, 220);
    }
    if (mode === "Flow") {
      return filtered.filter((node) => ["function", "api_endpoint"].includes(node.type)).slice(0, 220);
    }
    if (mode === "Community" && communities.length) {
      const ranked = communities.map((community) => community.name);
      return filtered
        .filter((node) => {
          const key = node.file_path ?? node.type;
          return ranked.includes(key);
        })
        .slice(0, 240);
    }
    return filtered.slice(0, 220);
  }, [enabledTypes, graph.nodes, mode, communities]);

  const communityPalette = ["#FFB59D", "#7CD7C4", "#D4BBFF", "#E8A55A", "#5DB872", "#FFD3B6", "#9EF9E5"];

  const flowNodes: Node[] = useMemo(
    () =>
      visibleNodes.map((node, index) => {
        let color = palette[node.type] ?? "#A09D96";
        let pos = { x: 0, y: 0 };
        if (mode === "Community" && communities.length) {
          const key = node.file_path ?? node.type;
          const cluster = communityIndex.get(key) ?? 0;
          const clusterCount = Math.max(communities.length, 1);
          const clusterAngle = (cluster / clusterCount) * Math.PI * 2;
          const clusterCx = Math.cos(clusterAngle) * 380 + 520;
          const clusterCy = Math.sin(clusterAngle) * 280 + 360;
          const local = index % 7;
          const localAngle = (local / 7) * Math.PI * 2;
          pos = { x: clusterCx + Math.cos(localAngle) * 60, y: clusterCy + Math.sin(localAngle) * 60 };
          color = communityPalette[cluster % communityPalette.length];
        } else {
          const ring = Math.floor(index / 18);
          const angle = (index % 18) * (Math.PI / 9);
          const radius = 150 + ring * 150;
          pos = { x: Math.cos(angle) * radius + 520, y: Math.sin(angle) * radius + 360 };
        }
        return {
          id: node.id,
          position: pos,
          data: { label: node.name.length > 28 ? `${node.name.slice(0, 25)}…` : node.name },
          style: nodeStyle(color)
        };
      }),
    [visibleNodes, mode, communities, communityIndex]
  );
  const ids = useMemo(() => new Set(flowNodes.map((node) => node.id)), [flowNodes]);
  const flowEdges: Edge[] = useMemo(
    () =>
      graph.edges
        .filter((edge) => ids.has(edge.source_id) && ids.has(edge.target_id))
        .slice(0, 600)
        .map((edge) => ({
          id: edge.id,
          source: edge.source_id,
          target: edge.target_id,
          label: edge.type,
          animated: ["calls", "routes_to", "reads_from", "writes_to"].includes(edge.type),
          style: { stroke: "rgba(124, 215, 196, 0.55)", strokeWidth: 1.2 },
          labelStyle: { fill: "var(--muted-dark)", fontSize: 10, fontFamily: "var(--font-mono)" },
          labelBgStyle: { fill: "rgba(33, 31, 27, 0.85)" }
        })),
    [graph.edges, ids]
  );

  function toggleType(type: string) {
    setEnabledTypes((current) => {
      const next = new Set(current);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <header>
        <span className="page-eyebrow">graph explorer <span className="rule" /> {visibleNodes.length} nodes visible</span>
        <h1 className="page-title" style={{ marginTop: 10 }}>Graph Explorer</h1>
        <p className="page-subtitle">Pan, zoom and inspect every extracted symbol. Switch lens to follow impact, architecture, or flow.</p>
      </header>

      <section className={clsx("graph-shell", !selected && "no-drawer")}>
        <div className="graph-stage">
          <div className="graph-toolbar">
            <div className="mode-tabs">
              {MODES.map((entry) => (
                <button
                  key={entry}
                  className={clsx("mode-tab", entry === mode && "active")}
                  onClick={() => setMode(entry)}
                >
                  {entry}
                </button>
              ))}
            </div>
            <div className="chip-row">
              {allTypes.slice(0, 12).map((type) => (
                <button
                  key={type}
                  className={clsx("filter-chip", enabledTypes.has(type) && "active")}
                  onClick={() => toggleType(type)}
                >
                  <span className="dot" style={{ color: palette[type] ?? "var(--muted-dark)" }} />
                  {type}
                </button>
              ))}
              {enabledTypes.size > 0 ? (
                <button className="filter-chip" onClick={() => setEnabledTypes(new Set())}>
                  reset
                </button>
              ) : null}
            </div>
          </div>

          <div className="graph-legend">
            {mode === "Community" && communities.length ? (
              <>
                {communities.slice(0, 6).map((community, idx) => (
                  <div key={community.name} className="row" style={{ color: communityPalette[idx % communityPalette.length] }}>
                    <span className="swatch" /> {shortLabel(community.name)} · {community.node_count}
                  </div>
                ))}
              </>
            ) : (
              <>
                <div className="row coral"><span className="swatch" /> Changed</div>
                <div className="row teal"><span className="swatch" /> Impacted</div>
                <div className="row muted"><span className="swatch" /> Unresolved ref</div>
              </>
            )}
          </div>

          <div className="graph-canvas">
            {visibleNodes.length === 0 ? (
              <div className="graph-empty">
                <h3>No graph yet</h3>
                <p>Build it first.</p>
                <code>devgraph build</code>
              </div>
            ) : (
              <ReactFlow
                nodes={flowNodes}
                edges={flowEdges}
                fitView
                onNodeClick={(_, node) => setSelected(graph.nodes.find((item) => item.id === node.id) ?? null)}
                onPaneClick={() => setSelected(null)}
                minZoom={0.2}
              >
                <MiniMap nodeColor={(node) => String((node.style as { background?: string }).background ?? "#A09D96")} pannable zoomable maskColor="rgba(14, 13, 11, 0.7)" />
                <Controls showInteractive={false} />
                <Background color="rgba(124, 215, 196, 0.10)" gap={28} />
              </ReactFlow>
            )}
          </div>
        </div>

        {selected ? (
          <motion.aside
            className="graph-drawer"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="drawer-head">
              <div>
                <span className="eyebrow"><FileCode size={12} /> node inspector</span>
                <h2>{selected.qualified_name}</h2>
                <span style={{ display: "inline-block", marginTop: 6, fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--muted-dark)" }}>
                  {selected.type} · {selected.file_path ?? "external"}
                </span>
              </div>
              <button className="icon-button" onClick={() => setSelected(null)}><X size={16} /></button>
            </div>

            <div className="drawer-confidence">
              <div>
                <span className="key">AI confidence</span>
                <span className="val">{(selected.confidence * 100).toFixed(1)}%</span>
              </div>
              <div className="tier-ring">{selected.confidence_tier.slice(0, 3)}</div>
            </div>

            <div className="drawer-section">
              <div className="head">Provenance</div>
              <div className="dense-list" style={{ maxHeight: 130 }}>
                <span><b>parser</b>{String(selected.metadata.parser ?? selected.confidence_tier)}</span>
                {selected.line_start ? <span><b>lines</b>L{selected.line_start}–{selected.line_end ?? selected.line_start}</span> : null}
                {selected.language ? <span><b>lang</b>{selected.language}</span> : null}
              </div>
            </div>

            {selected.summary ? (
              <div className="drawer-section">
                <div className="head">Summary</div>
                <p style={{ margin: 0, color: "var(--on-dark)", fontSize: 13, lineHeight: 1.6 }}>{selected.summary}</p>
              </div>
            ) : null}

            <div className="drawer-section">
              <div className="head">Core reference</div>
              <div className="drawer-snippet">
                <div className="file">
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                    <GitBranch size={12} /> {selected.file_path?.split(/[\\/]/).slice(-1)[0] ?? "node"} : L{selected.line_start ?? "?"}
                  </span>
                  <button className="icon-button" title="Copy path" onClick={() => navigator.clipboard?.writeText(selected.qualified_name)}>
                    <Copy size={12} />
                  </button>
                </div>
                <pre>{selected.qualified_name}{"\n"}{selected.summary ?? "(no summary extracted)"}</pre>
              </div>
            </div>

            {selected.tags.length ? (
              <div className="drawer-section">
                <div className="head">Tags</div>
                <div className="chip-row">
                  {selected.tags.slice(0, 8).map((tag) => (
                    <span key={tag} className="filter-chip">{tag}</span>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="drawer-actions">
              <button className="btn btn-primary btn-block"><Sparkles size={14} /> Explain in context</button>
              <button className="btn btn-secondary btn-block"><Network size={14} /> Show neighborhood</button>
              <button className="btn btn-coral-soft btn-block"><Copy size={14} /> Copy context pack</button>
            </div>
          </motion.aside>
        ) : null}
      </section>

      <section className="bento">
        <section className="glass-card col-4">
          <div className="card-head"><div><h3>Tip</h3><p className="subtitle">Reduce hairball.</p></div><Layers size={16} color="var(--muted-dark)" /></div>
          <p style={{ margin: 0, color: "var(--muted-dark)", fontSize: 13, lineHeight: 1.6 }}>
            Use mode tabs to focus the canvas. Toggle filter chips to narrow by node type, then click a node to load
            its inspector.
          </p>
        </section>
        <section className="glass-card col-4">
          <div className="card-head"><div><h3>Commands</h3><p className="subtitle">Companion CLI.</p></div><Code2 size={16} color="var(--muted-dark)" /></div>
          <div className="dense-list" style={{ maxHeight: 200 }}>
            <span><b>cli</b>devgraph explain &lt;file&gt;</span>
            <span><b>cli</b>devgraph review --json</span>
            <span><b>cli</b>devgraph handoff</span>
          </div>
        </section>
        <section className="glass-card col-4">
          <div className="card-head"><div><h3>Next</h3><p className="subtitle">Jump deeper.</p></div><ArrowRight size={16} color="var(--primary-coral-bright)" /></div>
          <div className="actions-stack">
            <button className="action-row" onClick={() => window.open("/api/graph", "_blank")}>
              <span className="lead"><ExternalLink size={14} className="ico muted" /> Inspect raw /api/graph</span>
              <span className="chev">→</span>
            </button>
          </div>
        </section>
      </section>
    </div>
  );
}

function shortLabel(name: string): string {
  const last = name.split(/[\\/]/).pop() ?? name;
  return last.length > 24 ? `${last.slice(0, 21)}…` : last;
}

function nodeStyle(color: string) {
  return {
    border: `1px solid ${color}`,
    borderRadius: 10,
    background: `linear-gradient(180deg, ${color}26, rgba(24, 23, 21, 0.92) 72%)`,
    boxShadow: `0 0 22px ${color}22`,
    color: "var(--on-dark)",
    minWidth: 140,
    padding: 9,
    fontFamily: "var(--font-mono)",
    fontSize: 11
  };
}
