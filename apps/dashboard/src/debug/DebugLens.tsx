import { useState } from "react";
import { Bug, Play, Route } from "lucide-react";
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

export function DebugLens({ graph }: { graph: GraphPayload }) {
  const [issue, setIssue] = useState("");
  const [result, setResult] = useState<DebugPayload | null>(null);
  const tests = graph.nodes.filter((node) => node.type === "test").slice(0, 12);

  async function runDebug() {
    const payload = await client.debug(issue);
    setResult(payload as DebugPayload);
  }

  return (
    <section className="lens debug-grid">
      <section className="glass-card wide-panel">
        <h2><Bug size={18} /> Debug Lens</h2>
        <textarea className="debug-input" value={issue} onChange={(event) => setIssue(event.target.value)} placeholder="Paste an error, stack trace, or symptom" />
        <button className="primary" onClick={() => void runDebug()}><Play size={15} /> Analyze</button>
      </section>
      <section className="glass-card">
        <h3>Parsed frames</h3>
        <div className="dense-list">
          {result?.stack_frames?.length ? result.stack_frames.map((frame, index) => (
            <span key={`${frame.file_path}-${index}`}><b>{frame.language ?? "frame"}</b>{frame.file_path}:{frame.line ?? "?"} {frame.function ?? ""}</span>
          )) : <em>No stack trace analyzed yet.</em>}
        </div>
      </section>
      <section className="glass-card">
        <h3><Route size={16} /> Suspected nodes</h3>
        <div className="dense-list">
          {result?.suspected_nodes?.length ? result.suspected_nodes.map((node) => (
            <span key={node.qualified_name}><b>{node.type}</b>{node.qualified_name}</span>
          )) : <em>No mapped graph nodes yet.</em>}
        </div>
      </section>
      <section className="glass-card">
        <h3>Recommended order</h3>
        <ol className="debug-order">
          {result?.recommended_debugging_order?.length ? result.recommended_debugging_order.map((item) => <li key={item}>{item}</li>) : <li>Paste a stack trace to generate an order.</li>}
        </ol>
      </section>
      <section className="glass-card">
        <h3>Related tests</h3>
        <div className="dense-list">
          {tests.length ? tests.map((node) => <span key={node.id}>{node.qualified_name}</span>) : <em>No tests found in the current graph view.</em>}
        </div>
      </section>
    </section>
  );
}
