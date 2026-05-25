import type { GraphPayload } from "@devgraph/schema";

export function KnowledgeLens({ graph }: { graph: GraphPayload }) {
  const docs = graph.nodes.filter((node) => node.type === "document" || node.type === "section");
  const configs = graph.nodes.filter((node) => node.type === "config");
  return (
    <section className="lens">
      <h2>Knowledge Lens</h2>
      <div className="knowledge-grid">
        <section className="panel">
          <h3>Docs</h3>
          {docs.slice(0, 20).map((node) => <p key={node.id}>{node.qualified_name}</p>)}
        </section>
        <section className="panel">
          <h3>Configs</h3>
          {configs.slice(0, 20).map((node) => <p key={node.id}>{node.qualified_name}</p>)}
        </section>
      </div>
    </section>
  );
}

