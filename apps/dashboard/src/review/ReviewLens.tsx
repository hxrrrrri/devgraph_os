import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ModeGraph } from "../graph/ModeGraph";
import { useDashboardStore } from "../store/dashboardStore";
import {
  AlertTriangle,
  Brain,
  Clipboard,
  Code2,
  Database,
  Flame,
  GitCompare,
  History,
  ShieldAlert,
  Sparkles
} from "lucide-react";
import type { ReviewResult } from "@devgraph/schema";

const severityClass: Record<string, string> = {
  high: "sev-high",
  medium: "sev-med",
  low: "sev-low"
};

const stagger = { show: { transition: { staggerChildren: 0.06 } } };
const rise = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] } }
};

export function ReviewLens({ review, onLoadReview }: { review: ReviewResult | null; onLoadReview: () => void }) {
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const severityEntries = useMemo(
    () =>
      review
        ? Object.entries(review.severity_by_file).sort((a, b) => severityRank(b[1]) - severityRank(a[1]))
        : [],
    [review]
  );
  const blastGraph = useMemo(() => buildBlastGraph(review), [review]);

  if (!review) {
    return (
      <div style={{ display: "grid", gap: 18 }}>
        <ReviewHeader onLoadReview={onLoadReview} />
        <ReviewSkeleton />
      </div>
    );
  }

  const offset = Math.max(0, 502 - (review.risk_score / 100) * 502);
  const firstHunk = (review.changed_hunks[0] ?? null) as Record<string, unknown> | null;
  const firstSnippet = Object.entries(review.changed_snippets)[0];

  return (
    <motion.div variants={stagger} initial="hidden" animate="show" style={{ display: "grid", gap: 22 }}>
      <ReviewHeader onLoadReview={onLoadReview} review={review} />
      <ReviewImpactGraph />

      <div className="review-grid">
        {/* Left column: risk + blast */}
        <div className="col-left">
          <motion.section className="glass-card" variants={rise}>
            <div className="card-head">
              <span className="card-label">Risk analysis</span>
              <span className={`risk-badge ${review.risk_level}`}>{review.risk_level}</span>
            </div>
            <div className="risk-gauge">
              <svg viewBox="0 0 192 192">
                <circle className="track" cx="96" cy="96" r="80" />
                <circle
                  className={`fill ${review.risk_level}`}
                  cx="96"
                  cy="96"
                  r="80"
                  strokeDasharray="502"
                  strokeDashoffset={offset}
                />
              </svg>
              <div className="center">
                <div className={`score ${review.risk_level}`}>{review.risk_score}</div>
                <div className="unit">percent risk</div>
              </div>
            </div>
            <div className="gauge-meta">
              <div>
                <div className="meta-row">
                  <span className="label">Changed symbols</span>
                  <span className="value">{review.changed_symbols.length}</span>
                </div>
                <div className="meta-bar"><i style={{ width: `${pct(review.changed_symbols.length, 20)}%` }} /></div>
              </div>
              <div>
                <div className="meta-row">
                  <span className="label">Test coverage void</span>
                  <span className="value">{review.missing_tests.length} files</span>
                </div>
                <div className="meta-bar amber"><i style={{ width: `${pct(review.missing_tests.length, 10)}%` }} /></div>
              </div>
              <div>
                <div className="meta-row">
                  <span className="label">Public API breaks</span>
                  <span className="value">{review.public_api_changes.length}</span>
                </div>
                <div className="meta-bar err"><i style={{ width: `${pct(review.public_api_changes.length, 6)}%` }} /></div>
              </div>
            </div>
            {review.risk_explanation.length ? (
              <div className="dense-list" style={{ marginTop: 16, maxHeight: 180 }}>
                {review.risk_explanation.slice(0, 4).map((reason) => (
                  <span key={reason}><b>why</b>{reason}</span>
                ))}
              </div>
            ) : null}
          </motion.section>

          <motion.section className="glass-card" variants={rise}>
            <span className="card-label">Blast radius</span>
            <div className="blast" style={{ marginTop: 14 }}>
              <svg viewBox="0 0 320 200" preserveAspectRatio="xMidYMid meet">
                {blastGraph.edges.map((edge, idx) => (
                  <line
                    key={`edge-${idx}`}
                    x1={edge.x1}
                    y1={edge.y1}
                    x2={edge.x2}
                    y2={edge.y2}
                    stroke="rgba(255, 181, 157, 0.42)"
                    strokeWidth={1}
                    strokeDasharray="3 3"
                  />
                ))}
                {blastGraph.nodes.map((node) => (
                  <g key={node.id}>
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={node.kind === "changed" ? 9 : 5.5}
                      fill={node.kind === "changed" ? "var(--primary-coral-bright)" : "var(--accent-teal)"}
                      stroke={node.kind === "changed" ? "rgba(255, 181, 157, 0.55)" : "rgba(124, 215, 196, 0.45)"}
                      strokeWidth={node.kind === "changed" ? 3 : 1.5}
                      style={{ filter: node.kind === "changed" ? "drop-shadow(0 0 8px rgba(255,181,157,0.5))" : "drop-shadow(0 0 5px rgba(124,215,196,0.35))" }}
                    >
                      <title>{node.label}</title>
                    </circle>
                  </g>
                ))}
              </svg>
              {blastGraph.nodes.length === 0 ? (
                <div className="core" style={{ background: "transparent", borderColor: "transparent", color: "var(--muted-dark)", fontFamily: "var(--font-mono)", fontSize: 10 }}>
                  no impact
                </div>
              ) : null}
            </div>
            <div className="blast-stats">
              <div>
                <div className="num">{pad(review.changed_nodes.length)}</div>
                <span className="key">Direct</span>
              </div>
              <div>
                <div className="num">{pad(review.impacted_nodes.length)}</div>
                <span className="key">Transitive</span>
              </div>
              <div>
                <div className="num">{pad(review.public_api_changes.length)}</div>
                <span className="key">API breaks</span>
              </div>
            </div>
          </motion.section>

          <motion.section className="glass-card" variants={rise}>
            <div className="card-head"><span className="card-label">Changed symbols</span><Code2 size={14} color="var(--muted-dark)" /></div>
            <div className="dense-list">
              {review.changed_symbols.length ? review.changed_symbols.slice(0, 14).map((node) => (
                <span key={node.id}><b>{node.type}</b>{node.qualified_name}</span>
              )) : <em>No diff hunks mapped to graph symbols.</em>}
            </div>
          </motion.section>
        </div>

        {/* Middle column: impacted files + diff */}
        <div className="col-mid">
          <div className="card-head" style={{ marginBottom: 4 }}>
            <h3 style={{ fontFamily: "var(--font-ui)" }}>Impacted files</h3>
            <span className="card-label">{review.impacted_files.length} total</span>
          </div>
          <motion.div variants={stagger} style={{ display: "grid", gap: 12 }}>
            {review.impacted_files.length ? review.impacted_files.slice(0, 6).map((file) => {
              const severity = review.severity_by_file[file] ?? "low";
              return (
                <motion.div key={file} className="file-card" variants={rise}>
                  <span className={clsxIco(severity)}>
                    <History size={16} />
                  </span>
                  <div>
                    <div className="head">
                      <span className="name">{shortName(file)}</span>
                      <span className={`risk-badge ${severityToLevel(severity)}`}>{severity}</span>
                    </div>
                    <span className="path">{file}</span>
                    <div className="stats">
                      <span className="stat"><Code2 size={12} /> {review.changed_symbols.filter((node) => node.file_path === file).length} symbols</span>
                      <span className="stat"><GitCompare size={12} /> {review.changed_hunks.filter((hunk) => hunk.file_path === file).length} hunks</span>
                    </div>
                  </div>
                </motion.div>
              );
            }) : <em style={{ color: "var(--muted-dark)" }}>No impacted files.</em>}
          </motion.div>

          {firstHunk ? (
            <motion.div className="diff-card" variants={rise}>
              <div className="diff-head">
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <GitCompare size={12} /> @@ {String(firstHunk.file_path)} : {String(firstHunk.new_start ?? "?")}
                </span>
                <span>{review.changed_hunks.length} hunks</span>
              </div>
              <pre>
                {firstSnippet ? formatDiffPreview(firstSnippet[1]) : "diff preview unavailable"}
              </pre>
            </motion.div>
          ) : null}

          <motion.section className="glass-card" variants={rise}>
            <div className="card-head"><span className="card-label">Severity heat map</span><Flame size={14} color="var(--muted-dark)" /></div>
            {severityEntries.length ? (
              <div className="severity-grid">
                {severityEntries.slice(0, 20).map(([file, sev]) => (
                  <span key={file} className={`severity-cell ${severityClass[sev] ?? ""}`} title={file}>
                    <b>{sev}</b>
                    <code>{shortName(file)}</code>
                  </span>
                ))}
              </div>
            ) : <em style={{ color: "var(--muted-dark)" }}>No severity signal — no migrations, API drift, or fan-out hotspots in this diff.</em>}
          </motion.section>

          {review.api_signature_changes.length || review.route_contract_changes.length || review.fan_out.length || review.infra_blast_radius.length ? (
            <motion.section className="glass-card" variants={rise}>
              <div className="card-head"><span className="card-label">Sensitive deltas</span><ShieldAlert size={14} color="var(--accent-amber)" /></div>
              <div className="dense-list">
                {review.api_signature_changes.slice(0, 4).map((entry, idx) => (
                  <span key={`api-${idx}`}><b>API</b>{String(entry.code)} · {String(entry.qualified_name ?? "")}</span>
                ))}
                {review.route_contract_changes.slice(0, 4).map((entry, idx) => (
                  <span key={`route-${idx}`}><b>route</b>{String(entry.code)} · {String(entry.method ?? "")} {String(entry.path ?? "")}</span>
                ))}
                {review.fan_out.slice(0, 4).map((entry, idx) => (
                  <span key={`fan-${idx}`}><b>{String(entry.fan_in ?? 0)}→{String(entry.fan_out ?? 0)}</b>{String(entry.qualified_name ?? "")}</span>
                ))}
                {review.infra_blast_radius.slice(0, 4).map((entry, idx) => (
                  <span key={`infra-${idx}`}><b>{String(entry.category ?? "infra")}</b>{String(entry.file_path ?? "")}</span>
                ))}
              </div>
            </motion.section>
          ) : null}
        </div>

        {/* Right column: critical checklist + AI quote + actions */}
        <div className="col-right">
          <motion.section className="glass-card" variants={rise} style={{ height: "100%" }}>
            <span className="card-label">Critical checklist</span>
            <div className="checklist" style={{ marginTop: 18 }}>
              {review.review_checklist.length ? review.review_checklist.slice(0, 6).map((item) => {
                const isChecked = checked.has(item);
                return (
                  <label
                    key={item}
                    className="check-item"
                    onClick={() => setChecked((prev) => {
                      const next = new Set(prev);
                      if (next.has(item)) next.delete(item); else next.add(item);
                      return next;
                    })}
                  >
                    <input type="checkbox" readOnly checked={isChecked} />
                    <span className="box" />
                    <div>
                      <span className="title">{checklistTitle(item)}</span>
                      <p className="desc">{item}</p>
                    </div>
                  </label>
                );
              }) : <em style={{ color: "var(--muted-dark)" }}>No checklist items generated.</em>}
            </div>

            <div className="drawer-actions" style={{ marginTop: 22 }}>
              <button className="btn btn-primary btn-block"><Sparkles size={14} /> Approve & merge</button>
              <button
                className="btn btn-coral-soft btn-block"
                onClick={() => navigator.clipboard?.writeText(review.context_pack)}
              >
                <Clipboard size={14} /> Copy context pack
              </button>
            </div>

            {review.suggested_commands.length ? (
              <div className="dense-list" style={{ marginTop: 18, maxHeight: 200 }}>
                {review.suggested_commands.slice(0, 4).map((cmd) => (
                  <span key={cmd}><b>cmd</b>{cmd}</span>
                ))}
              </div>
            ) : null}

            <div className="ai-quote">
              <span className="badge"><Brain size={16} /></span>
              <div>
                <span className="kind">Knowledge graph ai</span>
                <p className="body">
                  "{firstAiHint(review)}"
                </p>
              </div>
            </div>
          </motion.section>

          {review.database_or_schema_changes.length || review.security_sensitive_changes.length ? (
            <motion.section className="glass-card" variants={rise}>
              <div className="card-head"><span className="card-label">High-blast areas</span><Database size={14} color="var(--error)" /></div>
              <div className="dense-list">
                {review.database_or_schema_changes.slice(0, 4).map((entry) => (
                  <span key={entry} className="attention"><b>db</b>{entry}</span>
                ))}
                {review.security_sensitive_changes.slice(0, 4).map((entry) => (
                  <span key={entry} className="attention"><b>sec</b>{entry}</span>
                ))}
              </div>
            </motion.section>
          ) : null}
        </div>
      </div>
    </motion.div>
  );
}

function ReviewImpactGraph() {
  const changed = useDashboardStore((s) => s.changedNodeIds.size);
  const affected = useDashboardStore((s) => s.affectedNodeIds.size);
  if (changed === 0 && affected === 0) return null;
  return (
    <section className="glass-card dg-review-impact-card">
      <div className="card-head">
        <div>
          <h3>Impact graph</h3>
          <p className="subtitle">
            {changed} changed · {affected} affected · 1-hop neighbourhood. Click any node to inspect.
          </p>
        </div>
      </div>
      <div className="dg-review-impact-host">
        <ModeGraph mode="Impact" />
      </div>
    </section>
  );
}

function ReviewHeader({ review, onLoadReview }: { review?: ReviewResult; onLoadReview: () => void }) {
  return (
    <header>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 18, flexWrap: "wrap" }}>
        <div>
          <span className="page-eyebrow">review lens <span className="rule" /> cockpit</span>
          <h1 className="page-title" style={{ marginTop: 10 }}>Review Lens</h1>
          <p className="page-subtitle">
            {review
              ? `${review.changed_files.length} changed files · ${review.impacted_files.length} impacted · ${review.affected_tests.length} tests touched`
              : "Heuristic analysis of the current diff. Press review changes to run the engine."}
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-secondary" onClick={onLoadReview}><AlertTriangle size={14} /> Re-run review</button>
        </div>
      </div>
    </header>
  );
}

function ReviewSkeleton() {
  return (
    <div className="review-grid">
      <div className="col-left" style={{ display: "grid", gap: 18 }}>
        {Array.from({ length: 2 }).map((_, idx) => (
          <section key={idx} className="glass-card skeleton-card">
            <div className="skeleton-line lg" />
            <div className="skeleton-line" />
            <div className="skeleton-line" />
            <div className="skeleton-line short" />
          </section>
        ))}
      </div>
      <div className="col-mid" style={{ display: "grid", gap: 16 }}>
        {Array.from({ length: 3 }).map((_, idx) => (
          <section key={idx} className="glass-card skeleton-card">
            <div className="skeleton-line lg" />
            <div className="skeleton-line" />
            <div className="skeleton-line short" />
          </section>
        ))}
      </div>
      <div className="col-right" style={{ display: "grid", gap: 16 }}>
        <section className="glass-card skeleton-card">
          <div className="skeleton-line lg" />
          <div className="skeleton-line" />
          <div className="skeleton-line" />
          <div className="skeleton-line" />
        </section>
      </div>
    </div>
  );
}

function severityRank(severity: string): number {
  if (severity === "high") return 3;
  if (severity === "medium") return 2;
  if (severity === "low") return 1;
  return 0;
}

function severityToLevel(severity: string): string {
  if (severity === "high") return "high";
  if (severity === "medium") return "medium";
  return "low";
}

function pct(value: number, base: number): number {
  return Math.min(100, Math.round((value / Math.max(base, 1)) * 100));
}

function pad(value: number): string {
  return value.toString().padStart(2, "0");
}

function shortName(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

function clsxIco(severity: string): string {
  if (severity === "high") return "lead-ico";
  if (severity === "medium") return "lead-ico";
  return "lead-ico teal";
}

function checklistTitle(item: string): string {
  const match = item.match(/^(?:\[[^\]]+\]\s*)?([A-Za-z][^:.;]{2,40})/);
  return match ? match[1].trim() : "Review item";
}

type BlastNode = { id: string; x: number; y: number; kind: "changed" | "impacted"; label: string };
type BlastEdge = { x1: number; y1: number; x2: number; y2: number };

function buildBlastGraph(review: ReviewResult | null): { nodes: BlastNode[]; edges: BlastEdge[] } {
  if (!review) return { nodes: [], edges: [] };
  const changed = review.changed_nodes.slice(0, 4);
  const impacted = review.impacted_nodes.slice(0, 14);
  if (!changed.length && !impacted.length) return { nodes: [], edges: [] };

  const cx = 160;
  const cy = 100;
  const nodes: BlastNode[] = [];

  changed.forEach((node, idx, arr) => {
    const angle = arr.length === 1 ? 0 : (idx / arr.length) * Math.PI * 2;
    const r = arr.length === 1 ? 0 : 28;
    nodes.push({
      id: `c-${node.id}`,
      x: cx + Math.cos(angle) * r,
      y: cy + Math.sin(angle) * r,
      kind: "changed",
      label: node.qualified_name
    });
  });

  impacted.forEach((node, idx, arr) => {
    const angle = (idx / Math.max(arr.length, 1)) * Math.PI * 2;
    const r = 70 + (idx % 3) * 14;
    nodes.push({
      id: `i-${node.id}`,
      x: cx + Math.cos(angle) * r,
      y: cy + Math.sin(angle) * (r * 0.65),
      kind: "impacted",
      label: node.qualified_name
    });
  });

  const edges: BlastEdge[] = [];
  const changedNodes = nodes.filter((n) => n.kind === "changed");
  if (changedNodes.length) {
    nodes
      .filter((n) => n.kind === "impacted")
      .forEach((dst, idx) => {
        const src = changedNodes[idx % changedNodes.length];
        edges.push({ x1: src.x, y1: src.y, x2: dst.x, y2: dst.y });
      });
  }
  return { nodes, edges };
}

function firstAiHint(review: ReviewResult): string {
  if (review.warnings[0]) return review.warnings[0];
  if (review.prioritized_review_items[0]) return review.prioritized_review_items[0];
  if (review.risk_explanation[0]) return review.risk_explanation[0];
  return "Risk gauge synced. Run focused tests on the impacted files before merging.";
}

function formatDiffPreview(snippet: string): JSX.Element {
  const lines = snippet.split(/\r?\n/).slice(0, 16);
  return (
    <>
      {lines.map((line, idx) => {
        if (line.startsWith("+")) return <span key={idx} className="line add"><span className="ln">{idx + 1}</span>{line}</span>;
        if (line.startsWith("-")) return <span key={idx} className="line del"><span className="ln">{idx + 1}</span>{line}</span>;
        return <span key={idx} className="line"><span className="ln">{idx + 1}</span>{line}</span>;
      })}
    </>
  );
}
