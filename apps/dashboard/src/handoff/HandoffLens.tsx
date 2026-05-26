import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Copy, Download, FileJson, FileText, RefreshCw, Send, Sparkles } from "lucide-react";
import type { HandoffPayload } from "@devgraph/schema";
import { client } from "../api/client";

const rise = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } }
};

export function HandoffLens() {
  const [payload, setPayload] = useState<HandoffPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const next = await client.handoff();
      setPayload(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load handoff");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const data = (payload?.data ?? {}) as Record<string, unknown>;
  const branch = String(data.branch ?? "main");
  const changedFiles = (data.changed_files as string[] | undefined) ?? [];
  const changedSymbols = (data.changed_symbols as Array<Record<string, unknown>> | undefined) ?? [];
  const impactedFiles = (data.impacted_files as string[] | undefined) ?? [];
  const recentDecisions = (data.recent_decisions as Array<Record<string, unknown>> | undefined) ?? [];
  const todos = (data.todos as Array<Record<string, unknown>> | undefined) ?? [];
  const prompt = String(data.continuation_prompt ?? payload?.markdown ?? "");
  const freshness = String(data.graph_freshness ?? "unknown");

  return (
    <div style={{ display: "grid", gap: 22 }}>
      <header>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 18, flexWrap: "wrap" }}>
          <div>
            <span className="page-eyebrow">handoff lens <span className="rule" /> cross-agent transfer</span>
            <h1 className="page-title" style={{ marginTop: 10 }}>Handoff Lens</h1>
            <p className="page-subtitle">
              A reproducible snapshot you can paste into any other agent — branch, freshness, diffs, decisions and the continuation prompt.
            </p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-secondary" onClick={() => void load()}><RefreshCw size={14} /> Regenerate</button>
            <button
              className="btn btn-primary"
              disabled={!prompt}
              onClick={() => navigator.clipboard?.writeText(prompt)}
            >
              <Copy size={14} /> Copy prompt
            </button>
          </div>
        </div>
      </header>

      {error ? <div className="alert"><Sparkles size={14} /> {error}</div> : null}

      <motion.section className="kpi-grid" initial="hidden" animate="show">
        <motion.div className="kpi" variants={rise}>
          <div className="kpi-head"><span className="kpi-label">Branch</span></div>
          <span className="kpi-value">{branch}</span>
        </motion.div>
        <motion.div className="kpi" variants={rise}>
          <div className="kpi-head"><span className="kpi-label">Freshness</span></div>
          <span className="kpi-value">{freshness}</span>
        </motion.div>
        <motion.div className="kpi" variants={rise}>
          <div className="kpi-head"><span className="kpi-label">Changed files</span></div>
          <span className="kpi-value">{changedFiles.length}</span>
        </motion.div>
        <motion.div className="kpi" variants={rise}>
          <div className="kpi-head"><span className="kpi-label">Impacted files</span></div>
          <span className="kpi-value">{impactedFiles.length}</span>
        </motion.div>
      </motion.section>

      <div className="handoff-grid">
        <motion.section className="handoff-prompt" variants={rise} initial="hidden" animate="show">
          <div className="head">
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Send size={12} /> continuation prompt
            </span>
            <span>{prompt.length} chars</span>
          </div>
          <pre>{loading && !prompt ? "Loading handoff…" : prompt || "No handoff prompt yet. Run devgraph handoff."}</pre>
        </motion.section>

        <div style={{ display: "grid", gap: 18 }}>
          <motion.section className="glass-card" variants={rise} initial="hidden" animate="show">
            <div className="card-head"><div><h3>Changed symbols</h3><p className="subtitle">From the local diff.</p></div></div>
            <div className="dense-list">
              {changedSymbols.length ? changedSymbols.slice(0, 8).map((symbol, idx) => (
                <span key={`sym-${idx}`}>
                  <b>{String(symbol.type ?? "sym")}</b>{String(symbol.qualified_name ?? symbol.name ?? "")}
                </span>
              )) : <em>No changed symbols.</em>}
            </div>
          </motion.section>

          <motion.section className="glass-card" variants={rise} initial="hidden" animate="show">
            <div className="card-head"><div><h3>Open TODOs</h3><p className="subtitle">Inline notes you should pick up.</p></div></div>
            <div className="dense-list">
              {todos.length ? todos.slice(0, 6).map((todo, idx) => (
                <span key={`todo-${idx}`}>
                  <b>{String(todo.kind ?? "todo")}</b>{String(todo.text ?? todo.message ?? "")}
                </span>
              )) : <em>No open TODOs.</em>}
            </div>
          </motion.section>

          <motion.section className="glass-card" variants={rise} initial="hidden" animate="show">
            <div className="card-head"><div><h3>Recent decisions</h3><p className="subtitle">Memories and rejected attempts.</p></div></div>
            <div className="dense-list">
              {recentDecisions.length ? recentDecisions.slice(0, 6).map((decision, idx) => (
                <span key={`dec-${idx}`}>
                  <b>{String(decision.kind ?? "memory")}</b>{String(decision.content ?? "")}
                </span>
              )) : <em>No recent decisions logged.</em>}
            </div>
          </motion.section>

          <motion.section className="glass-card" variants={rise} initial="hidden" animate="show">
            <div className="card-head"><div><h3>Artifacts</h3><p className="subtitle">On-disk paths.</p></div></div>
            <div className="dense-list">
              <span><b><FileText size={11} /> md</b>{payload?.markdown_path ?? "(none)"}</span>
              <span><b><FileJson size={11} /> json</b>{payload?.json_path ?? "(none)"}</span>
            </div>
            <div className="drawer-actions" style={{ marginTop: 14 }}>
              <button
                className="btn btn-secondary btn-block"
                disabled={!payload?.markdown}
                onClick={() => downloadFile(payload?.markdown ?? "", "handoff.md", "text/markdown")}
              >
                <Download size={14} /> Download handoff.md
              </button>
              <button
                className="btn btn-coral-soft btn-block"
                disabled={!payload?.data}
                onClick={() => downloadFile(JSON.stringify(payload?.data ?? {}, null, 2), "handoff.json", "application/json")}
              >
                <Download size={14} /> Download handoff.json
              </button>
            </div>
          </motion.section>
        </div>
      </div>
    </div>
  );
}

function downloadFile(contents: string, name: string, mime: string) {
  const blob = new Blob([contents], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
