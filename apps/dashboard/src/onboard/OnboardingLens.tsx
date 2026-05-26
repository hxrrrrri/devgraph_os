import { motion } from "framer-motion";
import { BookOpen, Compass, Layers, ListChecks, Map, Waypoints } from "lucide-react";
import type { GraphPayload, GraphStatus } from "@devgraph/schema";

const rise = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } }
};

const TOUR_STEPS: Array<{ label: string; hint: string }> = [
  { label: "Docs & configs", hint: "Read first." },
  { label: "Architecture", hint: "Modules and services." },
  { label: "Key symbols", hint: "Hot functions and classes." },
  { label: "Flows", hint: "Calls, routes, reads, writes." },
  { label: "Review", hint: "Where new changes land." }
];

export function OnboardingLens({ status, graph }: { status: GraphStatus | null; graph: GraphPayload }) {
  const readFirst = graph.nodes
    .filter((node) => node.file_path && ["module", "class", "api_endpoint", "config", "document"].includes(node.type))
    .slice(0, 10);
  const flows = graph.edges.filter((edge) => ["calls", "routes_to", "depends_on"].includes(edge.type)).slice(0, 8);
  const keySymbols = graph.nodes
    .filter((node) => ["function", "class", "api_endpoint"].includes(node.type))
    .slice(0, 10);

  return (
    <div style={{ display: "grid", gap: 22 }}>
      <header>
        <span className="page-eyebrow">onboarding lens <span className="rule" /> first day in the repo</span>
        <h1 className="page-title" style={{ marginTop: 10 }}>Onboarding Lens</h1>
        <p className="page-subtitle">A short, opinionated guided tour over the freshly built graph.</p>
      </header>

      <motion.section className="glass-card" variants={rise} initial="hidden" animate="show">
        <div className="card-head"><div><h3><Compass size={16} /> Guided tour</h3><p className="subtitle">Five-step orientation.</p></div></div>
        <div className="tour">
          {TOUR_STEPS.map((step, idx) => (
            <span key={step.label}>
              <b>{idx + 1} · {step.label}</b>
              <span style={{ color: "var(--muted-dark)", fontSize: 12 }}>{step.hint}</span>
            </span>
          ))}
        </div>
      </motion.section>

      <div className="bento">
        <motion.section className="glass-card col-4" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3><Map size={16} /> Project shape</h3><p className="subtitle">Quick scale.</p></div></div>
          <p style={{ margin: 0, color: "var(--on-dark)", fontSize: 14, lineHeight: 1.6 }}>
            {status ? `${status.total_files} files · ${status.total_nodes} nodes · ${status.total_edges} edges · ${status.total_chunks} chunks.`
              : "No status loaded. Run devgraph build first."}
          </p>
          {status?.languages ? (
            <div className="dense-list" style={{ marginTop: 16, maxHeight: 180 }}>
              {Object.entries(status.languages).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([lang, count]) => (
                <span key={lang}><b>{count}</b>{lang}</span>
              ))}
            </div>
          ) : null}
        </motion.section>

        <motion.section className="glass-card col-4" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3><BookOpen size={16} /> Read first</h3><p className="subtitle">Best entry points.</p></div></div>
          <div className="dense-list">
            {readFirst.length ? readFirst.map((node) => (
              <span key={node.id}><b>{node.type}</b>{node.qualified_name}</span>
            )) : <em>No anchor nodes yet — run devgraph build.</em>}
          </div>
        </motion.section>

        <motion.section className="glass-card col-4" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3><Layers size={16} /> Key symbols</h3><p className="subtitle">Hot functions & classes.</p></div></div>
          <div className="dense-list">
            {keySymbols.length ? keySymbols.map((node) => (
              <span key={node.id}><b>{node.type}</b>{node.qualified_name}</span>
            )) : <em>No symbols yet.</em>}
          </div>
        </motion.section>

        <motion.section className="glass-card col-6" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3><Waypoints size={16} /> Top flows</h3><p className="subtitle">Most informative edges.</p></div></div>
          <div className="dense-list">
            {flows.length ? flows.map((edge) => (
              <span key={edge.id}><b>{edge.type}</b>{edge.provenance_source}</span>
            )) : <em>No flow edges yet.</em>}
          </div>
        </motion.section>

        <motion.section className="glass-card col-6" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3><ListChecks size={16} /> Suggested questions</h3><p className="subtitle">Use these inside Claude.</p></div></div>
          <div className="dense-list">
            <span><b>q1</b>What does this project do at a high level?</span>
            <span><b>q2</b>Where is the request lifecycle wired?</span>
            <span><b>q3</b>Which files are most security sensitive?</span>
            <span><b>q4</b>Which tests cover the auth flow?</span>
            <span><b>q5</b>What changed in the last week?</span>
          </div>
        </motion.section>
      </div>
    </div>
  );
}
