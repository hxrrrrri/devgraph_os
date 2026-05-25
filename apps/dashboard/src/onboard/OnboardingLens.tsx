import type { GraphStatus } from "@devgraph/schema";

export function OnboardingLens({ status }: { status: GraphStatus | null }) {
  return (
    <section className="lens">
      <h2>Onboarding Lens</h2>
      <section className="panel">
        <h3>Guided tour</h3>
        <ol>
          <li>Start with top-level documentation and configuration.</li>
          <li>Inspect modules with the highest graph degree.</li>
          <li>Use DevGraph explain for subsystem entry points.</li>
          <li>Run review before modifying public APIs or infrastructure.</li>
        </ol>
      </section>
      <section className="panel">
        <h3>Project shape</h3>
        <p>{status ? `${status.total_files} files, ${status.total_nodes} nodes, ${status.total_edges} edges.` : "No status loaded."}</p>
      </section>
    </section>
  );
}

