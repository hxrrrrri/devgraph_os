import type { GraphPayload } from "@devgraph/schema";

export function KnowledgeLens({ graph }: { graph: GraphPayload }) {
  const docs = graph.nodes.filter((node) => node.type === "document" || node.type === "section");
  const configs = graph.nodes.filter((node) => node.type === "config");
  const linkedDocs = graph.edges.filter((edge) => edge.type === "documents").length;
  const coverage = graph.nodes.length ? Math.round(((docs.length + configs.length) / graph.nodes.length) * 100) : 0;
  return (
    <section className="lens">
      <div className="knowledge-grid">
        <section className="glass-card">
          <h3>Knowledge coverage</h3>
          <strong className="coverage">{coverage}%</strong>
          <p>{docs.length} docs/sections, {configs.length} configs, {linkedDocs} docs-code links.</p>
        </section>
        <section className="glass-card">
          <h3>Stale docs candidates</h3>
          <div className="dense-list">
            {docs.slice(0, 8).map((node) => <span key={node.id}>{node.qualified_name}</span>)}
          </div>
        </section>
        <section className="glass-card">
          <h3>Docs</h3>
          <div className="dense-list">
            {docs.slice(0, 20).map((node) => <span key={node.id}>{node.qualified_name}</span>)}
          </div>
        </section>
        <section className="glass-card">
          <h3>Configs</h3>
          <div className="dense-list">
            {configs.slice(0, 20).map((node) => <span key={node.id}>{node.qualified_name}</span>)}
          </div>
        </section>
      </div>
    </section>
  );
}
