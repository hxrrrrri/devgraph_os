import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Copy, Network, Sparkles, X, FileCode, GitBranch, BookOpen, ShieldCheck } from "lucide-react";
import clsx from "clsx";
import { useDashboardStore } from "../store/dashboardStore";
import { client } from "../api/client";

type NodeDetail = {
  node: { id: string; qualified_name: string; type: string; file_path?: string | null; line_start?: number | null; line_end?: number | null; language?: string | null; summary?: string | null; confidence: number; confidence_tier: string; tags: string[]; metadata: Record<string, unknown> };
  chunks: Array<{ id: string; content: string; line_start?: number | null; line_end?: number | null }>;
  provenance: Array<{ id: string; source: string; source_path?: string | null; confidence_tier: string; line_start?: number | null; line_end?: number | null }>;
  neighborhood: { nodes: Array<{ id: string; qualified_name: string; type: string }>; edges: Array<{ id: string; source_id: string; target_id: string; type: string }> };
};

type TabKey = "overview" | "source" | "relations" | "provenance" | "impact";
const TABS: ReadonlyArray<{ id: TabKey; label: string; icon: typeof FileCode }> = [
  { id: "overview", label: "Overview", icon: BookOpen },
  { id: "source", label: "Source", icon: FileCode },
  { id: "relations", label: "Relations", icon: Network },
  { id: "provenance", label: "Provenance", icon: ShieldCheck },
  { id: "impact", label: "Impact", icon: GitBranch },
];

export function NodeInspector() {
  const selectedNodeId = useDashboardStore((s) => s.selectedNodeId);
  const nodesById = useDashboardStore((s) => s.nodesById);
  const changedNodeIds = useDashboardStore((s) => s.changedNodeIds);
  const affectedNodeIds = useDashboardStore((s) => s.affectedNodeIds);
  const selectNode = useDashboardStore((s) => s.selectNode);
  const [tab, setTab] = useState<TabKey>("overview");
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fallbackNode = selectedNodeId ? nodesById.get(selectedNodeId) ?? null : null;

  useEffect(() => {
    if (!selectedNodeId) {
      setDetail(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    client
      .node(selectedNodeId)
      .then((payload) => {
        if (cancelled) return;
        setDetail(payload as NodeDetail);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Unable to load node");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedNodeId]);

  const relations = useMemo(() => {
    if (!detail) return { callers: [], callees: [], importers: [], imports: [], tests: [], docs: [] };
    const groups = {
      callers: [] as Array<{ node: NodeDetail["neighborhood"]["nodes"][number]; type: string }>,
      callees: [] as Array<{ node: NodeDetail["neighborhood"]["nodes"][number]; type: string }>,
      importers: [] as Array<{ node: NodeDetail["neighborhood"]["nodes"][number]; type: string }>,
      imports: [] as Array<{ node: NodeDetail["neighborhood"]["nodes"][number]; type: string }>,
      tests: [] as Array<{ node: NodeDetail["neighborhood"]["nodes"][number]; type: string }>,
      docs: [] as Array<{ node: NodeDetail["neighborhood"]["nodes"][number]; type: string }>,
    };
    const nodeMap = new Map(detail.neighborhood.nodes.map((n) => [n.id, n]));
    for (const edge of detail.neighborhood.edges) {
      const other = edge.source_id === detail.node.id ? edge.target_id : edge.source_id;
      const node = nodeMap.get(other);
      if (!node) continue;
      const outgoing = edge.source_id === detail.node.id;
      if (edge.type === "calls") (outgoing ? groups.callees : groups.callers).push({ node, type: edge.type });
      else if (edge.type === "imports") (outgoing ? groups.imports : groups.importers).push({ node, type: edge.type });
      else if (edge.type === "tested_by") groups.tests.push({ node, type: edge.type });
      else if (edge.type === "documents") groups.docs.push({ node, type: edge.type });
    }
    return groups;
  }, [detail]);

  if (!selectedNodeId || !fallbackNode) return null;

  const node = detail?.node ?? fallbackNode;
  const isChanged = changedNodeIds.has(node.id);
  const isAffected = affectedNodeIds.has(node.id);

  return (
    <motion.aside
      className="graph-drawer dg-inspector"
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="drawer-head">
        <div>
          <span className="eyebrow"><FileCode size={12} /> node inspector</span>
          <h2 title={node.qualified_name}>{node.qualified_name}</h2>
          <span className="dg-inspector-sub">
            {node.type} · {(node.file_path ?? "external")}
            {node.line_start ? ` · L${node.line_start}` : ""}
          </span>
          {(isChanged || isAffected) ? (
            <span className={clsx("dg-inspector-status", isChanged ? "is-changed" : "is-affected")}>
              {isChanged ? "changed in this review" : "impacted by review"}
            </span>
          ) : null}
        </div>
        <button className="icon-button" onClick={() => selectNode(null)} aria-label="Close inspector">
          <X size={16} />
        </button>
      </div>

      <div className="dg-inspector-tabs">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              className={clsx("dg-inspector-tab", t.id === tab && "active")}
              onClick={() => setTab(t.id)}
            >
              <Icon size={12} /> {t.label}
            </button>
          );
        })}
      </div>

      {error ? <div className="alert" style={{ margin: "10px 0" }}>{error}</div> : null}
      {loading && !detail ? <div className="dg-inspector-loading">loading…</div> : null}

      <div className="dg-inspector-body">
        {tab === "overview" ? (
          <>
            <div className="drawer-section">
              <div className="head">Summary</div>
              <p className="dg-inspector-summary">
                {node.summary ?? "(no summary extracted)"}
              </p>
            </div>
            <div className="drawer-section">
              <div className="head">Confidence</div>
              <div className="dense-list" style={{ maxHeight: 80 }}>
                <span><b>tier</b>{node.confidence_tier}</span>
                <span><b>score</b>{(node.confidence * 100).toFixed(1)}%</span>
                {node.language ? <span><b>lang</b>{node.language}</span> : null}
              </div>
            </div>
            {node.tags.length ? (
              <div className="drawer-section">
                <div className="head">Tags</div>
                <div className="chip-row">
                  {node.tags.slice(0, 12).map((tag) => (
                    <span key={tag} className="filter-chip">{tag}</span>
                  ))}
                </div>
              </div>
            ) : null}
          </>
        ) : null}

        {tab === "source" ? (
          <div className="drawer-section">
            <div className="head">Source excerpts</div>
            {detail?.chunks.length ? (
              <div className="dg-inspector-chunks">
                {detail.chunks.slice(0, 4).map((chunk) => (
                  <pre key={chunk.id} className="dg-inspector-chunk">
                    {chunk.line_start ? <span className="dg-chunk-lines">L{chunk.line_start}{chunk.line_end ? `-${chunk.line_end}` : ""}</span> : null}
                    {chunk.content}
                  </pre>
                ))}
              </div>
            ) : (
              <em>No chunks indexed for this file.</em>
            )}
          </div>
        ) : null}

        {tab === "relations" ? (
          <div className="dg-inspector-relations">
            {([
              ["Callers", relations.callers],
              ["Callees", relations.callees],
              ["Importers", relations.importers],
              ["Imports", relations.imports],
              ["Tests", relations.tests],
              ["Docs", relations.docs],
            ] as const).map(([label, items]) => (
              <div key={label} className="drawer-section">
                <div className="head">{label} · {items.length}</div>
                <div className="dense-list" style={{ maxHeight: 140 }}>
                  {items.length ? items.slice(0, 12).map(({ node: rel }) => (
                    <button key={rel.id} className="dg-relation-row" onClick={() => selectNode(rel.id)}>
                      <b>{rel.type}</b>{rel.qualified_name}
                    </button>
                  )) : <em style={{ color: "var(--muted-dark)" }}>none</em>}
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {tab === "provenance" ? (
          <div className="drawer-section">
            <div className="head">Provenance</div>
            {detail?.provenance.length ? (
              <div className="dense-list" style={{ maxHeight: 220 }}>
                {detail.provenance.map((row) => (
                  <span key={row.id}>
                    <b>{row.source}</b>
                    {(row.source_path ?? "")} {row.line_start ? `· L${row.line_start}` : ""}
                  </span>
                ))}
              </div>
            ) : (
              <em>No provenance recorded.</em>
            )}
          </div>
        ) : null}

        {tab === "impact" ? (
          <div className="drawer-section">
            <div className="head">Review impact</div>
            <div className="dense-list" style={{ maxHeight: 220 }}>
              <span><b>changed</b>{isChanged ? "yes" : "no"}</span>
              <span><b>affected</b>{isAffected ? "yes" : "no"}</span>
              <span><b>neighbors</b>{detail?.neighborhood.nodes.length ?? 0}</span>
              <span><b>edges</b>{detail?.neighborhood.edges.length ?? 0}</span>
            </div>
          </div>
        ) : null}
      </div>

      <div className="drawer-actions">
        <button className="btn btn-primary btn-block"><Sparkles size={14} /> Explain in context</button>
        <button className="btn btn-coral-soft btn-block" onClick={() => navigator.clipboard?.writeText(node.qualified_name)}>
          <Copy size={14} /> Copy qualified name
        </button>
        <button
          className="btn btn-secondary btn-block"
          onClick={() => navigator.clipboard?.writeText(node.id)}
        >
          <Copy size={14} /> Copy node id
        </button>
      </div>
    </motion.aside>
  );
}
