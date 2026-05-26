import clsx from "clsx";
import { BookOpen, GraduationCap, Microscope, ShieldCheck, Sparkles, X, Bot } from "lucide-react";
import { useDashboardStore, type Persona } from "../store/dashboardStore";

const PERSONAS: ReadonlyArray<{ id: Persona; label: string; icon: typeof BookOpen; blurb: string }> = [
  { id: "junior", label: "Junior", icon: GraduationCap, blurb: "Explanations assume little prior knowledge of the codebase." },
  { id: "senior", label: "Senior", icon: BookOpen, blurb: "Concise summaries, points out architectural intent." },
  { id: "reviewer", label: "Reviewer", icon: ShieldCheck, blurb: "Focus on risk, blast radius, test coverage." },
  { id: "architect", label: "Architect", icon: Microscope, blurb: "Layer boundaries, coupling, contracts." },
  { id: "ai-agent", label: "AI agent", icon: Bot, blurb: "Structured context, ids, paths, exact relations." },
];

function personaExplanation(persona: Persona, layerName: string | null, nodeName: string | null): string {
  if (nodeName) {
    switch (persona) {
      case "junior":
        return `${nodeName} is a piece of code in this project. Look at its callers/callees in the Relations tab to see how it fits.`;
      case "senior":
        return `${nodeName} — inspect summary + neighbours to confirm intent. Use Path Finder to trace upstream/downstream.`;
      case "reviewer":
        return `Check whether ${nodeName} is in the diff overlay. If so, confirm tests cover the changed lines and the blast radius is bounded.`;
      case "architect":
        return `${nodeName} sits in the ${layerName ?? "app"} layer. Confirm it does not cross-cut into another layer's responsibility.`;
      case "ai-agent":
        return `node:${nodeName} layer:${layerName ?? "unknown"} — fetch /api/node/<id> for chunks + neighborhood, then summarise.`;
    }
  }
  if (layerName) {
    switch (persona) {
      case "junior":
        return `${layerName} is one of nine architecture buckets. Drill in to see the files grouped by folder.`;
      case "senior":
        return `${layerName} groups files by responsibility, not by directory. Use the inspector to see real dependencies.`;
      case "reviewer":
        return `Look for high-risk or many-affected counts on ${layerName}. Those are the layers to triage first.`;
      case "architect":
        return `${layerName}'s edge weight in the overview tells you how chatty it is with the rest of the system.`;
      case "ai-agent":
        return `layer:${layerName} — fetch /api/layers/${layerName.toLowerCase()} for nodes+edges scoped to this bucket.`;
    }
  }
  switch (persona) {
    case "junior":
      return "Pick a layer in the overview to start. Click any node for its inspector.";
    case "senior":
      return "Use the toolbar modes (Architecture / Impact / Flow) to refocus the canvas.";
    case "reviewer":
      return "Toggle diff in the toolbar. Coral = changed, teal = impacted.";
    case "architect":
      return "Start with the architecture overview. Layer cluster size tells you where complexity lives.";
    case "ai-agent":
      return "All endpoints are localhost-only. Start from /api/architecture and walk to /api/layers/<id>, /api/node/<id>.";
  }
}

export function LearnPanel() {
  const persona = useDashboardStore((s) => s.persona);
  const setPersona = useDashboardStore((s) => s.setPersona);
  const selectedNodeId = useDashboardStore((s) => s.selectedNodeId);
  const nodesById = useDashboardStore((s) => s.nodesById);
  const layers = useDashboardStore((s) => s.layers);
  const activeLayerId = useDashboardStore((s) => s.activeLayerId);
  const nodeIdToLayerId = useDashboardStore((s) => s.nodeIdToLayerId);
  const fileExplorerOpen = useDashboardStore((s) => s.fileExplorerOpen);
  const toggleFileExplorer = useDashboardStore((s) => s.toggleFileExplorer);

  const node = selectedNodeId ? nodesById.get(selectedNodeId) : null;
  const layerId = activeLayerId ?? (selectedNodeId ? nodeIdToLayerId.get(selectedNodeId) : null);
  const layer = layerId ? layers.find((l) => l.id === layerId) ?? null : null;
  const explanation = personaExplanation(persona, layer?.name ?? null, node?.qualified_name ?? null);

  return (
    <section className={clsx("dg-learn-panel", fileExplorerOpen && "with-file-explorer")}>
      <header className="dg-learn-head">
        <span className="eyebrow"><Sparkles size={12} /> learn panel</span>
        <button
          className="btn btn-secondary btn-tiny"
          onClick={toggleFileExplorer}
          title="Toggle file explorer"
        >
          <BookOpen size={12} /> files
        </button>
      </header>
      <div className="dg-persona-tabs" role="tablist">
        {PERSONAS.map((p) => {
          const Icon = p.icon;
          return (
            <button
              key={p.id}
              role="tab"
              aria-selected={persona === p.id}
              className={clsx("dg-persona-tab", persona === p.id && "active")}
              onClick={() => setPersona(p.id)}
              title={p.blurb}
            >
              <Icon size={12} /> {p.label}
            </button>
          );
        })}
      </div>
      <div className="dg-learn-body">
        <p className="dg-learn-blurb">{PERSONAS.find((p) => p.id === persona)?.blurb}</p>
        <div className="dg-learn-context">
          <span className="dg-learn-context-eyebrow">in context</span>
          <p>{explanation}</p>
        </div>
        {node ? (
          <div className="dg-learn-tags">
            <span className="dg-badge badge-affected">node · {node.type}</span>
            {layer ? <span className="dg-badge badge-match">layer · {layer.name}</span> : null}
          </div>
        ) : null}
      </div>
      <button
        className="dg-learn-close icon-button"
        onClick={() => {
          if (fileExplorerOpen) toggleFileExplorer();
        }}
        aria-label="Hide ancillary panels"
      >
        <X size={14} />
      </button>
    </section>
  );
}
