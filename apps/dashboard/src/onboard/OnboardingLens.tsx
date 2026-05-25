import type { GraphPayload, GraphStatus } from "@devgraph/schema";

export function OnboardingLens({ status, graph }: { status: GraphStatus | null; graph: GraphPayload }) {
  const readFirst = graph.nodes
    .filter((node) => node.file_path && ["module", "class", "api_endpoint", "config", "document"].includes(node.type))
    .slice(0, 8);
  const flows = graph.edges.filter((edge) => ["calls", "routes_to", "depends_on"].includes(edge.type)).slice(0, 6);
  return (
    <section className="lens">
      <section className="glass-card">
        <h3>Guided tour</h3>
        <div className="tour">
          {["Docs/config", "Architecture", "Key symbols", "Flows", "Review"].map((item, index) => (
            <span key={item}><b>{index + 1}</b>{item}</span>
          ))}
        </div>
      </section>
      <section className="glass-card">
        <h3>Project shape</h3>
        <p>{status ? `${status.total_files} files, ${status.total_nodes} nodes, ${status.total_edges} edges.` : "No status loaded."}</p>
      </section>
      <section className="glass-card">
        <h3>Read first</h3>
        <div className="dense-list">
          {readFirst.length ? readFirst.map((node) => <span key={node.id}><b>{node.type}</b>{node.qualified_name}</span>) : <em>No graph nodes loaded.</em>}
        </div>
      </section>
      <section className="glass-card">
        <h3>Top flows</h3>
        <div className="dense-list">
          {flows.length ? flows.map((edge) => <span key={edge.id}><b>{edge.type}</b>{edge.provenance_source}</span>) : <em>No flow edges found.</em>}
        </div>
      </section>
    </section>
  );
}
