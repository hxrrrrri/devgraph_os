import { motion } from "framer-motion";
import { BookMarked, FileCog, FileText, Link2 } from "lucide-react";
import type { GraphPayload } from "@devgraph/schema";

const rise = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } }
};

export function KnowledgeLens({ graph }: { graph: GraphPayload }) {
  const docs = graph.nodes.filter((node) => node.type === "document" || node.type === "section");
  const configs = graph.nodes.filter((node) => node.type === "config");
  const linkedDocs = graph.edges.filter((edge) => edge.type === "documents").length;
  const coverage = graph.nodes.length ? Math.round(((docs.length + configs.length) / graph.nodes.length) * 100) : 0;
  return (
    <div style={{ display: "grid", gap: 22 }}>
      <header>
        <span className="page-eyebrow">knowledge lens <span className="rule" /> docs and configs</span>
        <h1 className="page-title" style={{ marginTop: 10 }}>Knowledge Lens</h1>
        <p className="page-subtitle">Documentation surface, config files, and the live link between them and the code graph.</p>
      </header>

      <div className="bento">
        <motion.section className="glass-card col-4" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3><BookMarked size={16} /> Knowledge coverage</h3><p className="subtitle">Docs + configs over total nodes.</p></div></div>
          <span className="coverage">{coverage}%</span>
          <p style={{ marginTop: 12, color: "var(--muted-dark)", fontSize: 13 }}>
            {docs.length} docs/sections · {configs.length} configs · {linkedDocs} docs↔code links.
          </p>
        </motion.section>

        <motion.section className="glass-card col-4" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3><FileText size={16} /> Docs</h3><p className="subtitle">Markdown & RST.</p></div></div>
          <div className="dense-list">
            {docs.length ? docs.slice(0, 20).map((node) => <span key={node.id}>{node.qualified_name}</span>) : <em>No docs indexed.</em>}
          </div>
        </motion.section>

        <motion.section className="glass-card col-4" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3><FileCog size={16} /> Configs</h3><p className="subtitle">YAML, JSON, TOML.</p></div></div>
          <div className="dense-list">
            {configs.length ? configs.slice(0, 20).map((node) => <span key={node.id}>{node.qualified_name}</span>) : <em>No config files indexed.</em>}
          </div>
        </motion.section>

        <motion.section className="glass-card col-12" variants={rise} initial="hidden" animate="show">
          <div className="card-head"><div><h3><Link2 size={16} /> Stale-doc candidates</h3><p className="subtitle">Docs that may no longer match the code.</p></div></div>
          <div className="dense-list">
            {docs.length ? docs.slice(0, 12).map((node) => <span key={node.id}><b>doc</b>{node.qualified_name}</span>) : <em>No candidates yet.</em>}
          </div>
        </motion.section>
      </div>
    </div>
  );
}
