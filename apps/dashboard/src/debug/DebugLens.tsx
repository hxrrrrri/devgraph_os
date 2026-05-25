import { useState } from "react";
import { motion } from "framer-motion";
import { Bug, Play, Route, TestTube } from "lucide-react";
import type { GraphPayload } from "@devgraph/schema";
import { client } from "../api/client";

type DebugPayload = {
  error_type?: string | null;
  error_message?: string | null;
  stack_frames?: Array<{ file_path?: string; line?: number; function?: string; language?: string }>;
  suspected_nodes?: Array<{ qualified_name: string; type: string; line_start?: number; line_end?: number }>;
  related_configs?: string[];
  recommended_debugging_order?: string[];
  context_pack?: string;
};

const rise = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } }
};

export function DebugLens({ graph }: { graph: GraphPayload }) {
  const [issue, setIssue] = useState("");
  const [result, setResult] = useState<DebugPayload | null>(null);
  const [running, setRunning] = useState(false);
  const tests = graph.nodes.filter((node) => node.type === "test").slice(0, 12);

  async function runDebug() {
    setRunning(true);
    try {
      const payload = await client.debug(issue);
      setResult(payload as DebugPayload);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 22 }}>
      <header>
        <span className="page-eyebrow">debug lens <span className="rule" /> stack-trace triage</span>
        <h1 className="page-title" style={{ marginTop: 10 }}>Debug Lens</h1>
        <p className="page-subtitle">Paste an error, get parsed frames mapped to graph nodes, suggested next steps and related tests.</p>
      </header>

      <motion.section className="glass-card" variants={rise} initial="hidden" animate="show">
        <div className="card-head">
          <div><h3><Bug size={16} /> Input</h3><p className="subtitle">Paste raw stack trace or symptom.</p></div>
        </div>
        <textarea
          className="debug-input"
          value={issue}
          onChange={(event) => setIssue(event.target.value)}
          placeholder={"Traceback (most recent call last):\n  File \"app/main.py\", line 42, in <module>\n    run()"}
        />
        <div style={{ marginTop: 14, display: "flex", gap: 10 }}>
          <button className="btn btn-primary" onClick={() => void runDebug()} disabled={running || !issue.trim()}>
            <Play size={14} /> {running ? "Analyzing…" : "Analyze"}
          </button>
          <button className="btn btn-ghost" onClick={() => { setIssue(""); setResult(null); }}>Clear</button>
        </div>
      </motion.section>

      <div className="bento">
        <motion.section className="glass-card col-6" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3>Parsed frames</h3><p className="subtitle">Extracted from the stack trace.</p></div></div>
          <div className="dense-list">
            {result?.stack_frames?.length ? result.stack_frames.map((frame, idx) => (
              <span key={`${frame.file_path}-${idx}`}><b>{frame.language ?? "frame"}</b>{frame.file_path}:{frame.line ?? "?"} {frame.function ?? ""}</span>
            )) : <em>No frames yet. Paste a trace.</em>}
          </div>
        </motion.section>
        <motion.section className="glass-card col-6" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3><Route size={16} /> Suspected nodes</h3><p className="subtitle">Mapped onto the graph.</p></div></div>
          <div className="dense-list">
            {result?.suspected_nodes?.length ? result.suspected_nodes.map((node) => (
              <span key={node.qualified_name}><b>{node.type}</b>{node.qualified_name}</span>
            )) : <em>No mapped graph nodes yet.</em>}
          </div>
        </motion.section>

        <motion.section className="glass-card col-6" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3>Recommended order</h3><p className="subtitle">Step-by-step debugging plan.</p></div></div>
          <ol className="debug-order">
            {result?.recommended_debugging_order?.length ? result.recommended_debugging_order.map((item) => (
              <li key={item}>{item}</li>
            )) : <li>Paste a stack trace to generate an order.</li>}
          </ol>
        </motion.section>
        <motion.section className="glass-card col-6" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3><TestTube size={16} /> Related tests</h3><p className="subtitle">From current graph view.</p></div></div>
          <div className="dense-list">
            {tests.length ? tests.map((node) => <span key={node.id}>{node.qualified_name}</span>) : <em>No tests found.</em>}
          </div>
        </motion.section>

        {result?.context_pack ? (
          <motion.section className="glass-card col-12" variants={rise} initial="hidden" animate="show">
            <div className="card-head"><div><h3>Context pack</h3><p className="subtitle">Hand this to an AI agent.</p></div></div>
            <pre className="snippet">{result.context_pack}</pre>
          </motion.section>
        ) : null}
      </div>
    </div>
  );
}
