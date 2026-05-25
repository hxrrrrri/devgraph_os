import type { GraphPayload } from "@devgraph/schema";

export function DebugLens({ graph }: { graph: GraphPayload }) {
  const tests = graph.nodes.filter((node) => node.type === "test").slice(0, 12);
  return (
    <section className="lens">
      <h2>Debug Lens</h2>
      <textarea className="debug-input" placeholder="Paste an error, stack trace, or symptom" />
      <section className="panel">
        <h3>Related tests</h3>
        {tests.length ? tests.map((node) => <p key={node.id}>{node.qualified_name}</p>) : <p>No tests found in the current graph view.</p>}
      </section>
    </section>
  );
}

