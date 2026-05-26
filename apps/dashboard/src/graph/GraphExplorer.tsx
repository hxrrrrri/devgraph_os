import clsx from "clsx";
import { ArrowRight, Code2, ExternalLink, Layers } from "lucide-react";
import { useEffect, useMemo } from "react";
import { useDashboardStore } from "../store/dashboardStore";
import { deriveArchitecture } from "./graphAdapter";
import { ArchitectureOverview } from "./ArchitectureOverview";
import { LayerDetailGraph } from "./LayerDetailGraph";
import { ModeGraph } from "./ModeGraph";
import { GraphToolbar } from "./GraphToolbar";
import { NodeInspector } from "./NodeInspector";
import { PathFinderModal } from "./PathFinderModal";
import { FileExplorer } from "./FileExplorer";
import { CodeViewer } from "./CodeViewer";
import { LearnPanel } from "../onboard/LearnPanel";

export function GraphExplorer() {
  const graph = useDashboardStore((s) => s.graph);
  const layers = useDashboardStore((s) => s.layers);
  const setLayers = useDashboardStore((s) => s.setLayers);
  const navigationLevel = useDashboardStore((s) => s.navigationLevel);
  const graphMode = useDashboardStore((s) => s.graphMode);
  const selectedNodeId = useDashboardStore((s) => s.selectedNodeId);
  const fileExplorerOpen = useDashboardStore((s) => s.fileExplorerOpen);
  const codeViewerOpen = useDashboardStore((s) => s.codeViewerOpen);

  // Recompute layers whenever the graph payload changes. Cheap O(N+E).
  const derivation = useMemo(() => deriveArchitecture(graph), [graph]);
  useEffect(() => {
    setLayers(derivation.layers);
  }, [derivation, setLayers]);

  const layerCount = layers.length;
  const totalNodes = graph.nodes.length;
  const totalEdges = graph.edges.length;

  return (
    <div className="dg-graph-explorer" style={{ display: "grid", gap: 18 }}>
      <header>
        <span className="page-eyebrow">graph cockpit <span className="rule" /> {layerCount} layers · {totalNodes} nodes · {totalEdges} edges</span>
        <h1 className="page-title" style={{ marginTop: 10 }}>Graph Explorer</h1>
        <p className="page-subtitle">
          Architecture overview, drilldown, and review impact in one canvas. Click a layer to dive in, click a node to inspect.
        </p>
      </header>

      <section className={clsx("graph-shell", !selectedNodeId && "no-drawer", fileExplorerOpen && "with-file-tree")}>
        {fileExplorerOpen ? <FileExplorer /> : null}
        <div className="graph-stage">
          <GraphToolbar />
          {navigationLevel === "layer-detail" ? (
            <LayerDetailGraph />
          ) : graphMode === "Overview" || graphMode === "Architecture" ? (
            <ArchitectureOverview />
          ) : (
            <ModeGraph mode={graphMode} />
          )}
        </div>
        {selectedNodeId ? <NodeInspector /> : null}
      </section>

      <LearnPanel />
      <PathFinderModal />
      {codeViewerOpen ? <CodeViewer /> : null}

      <section className="bento">
        <section className="glass-card col-4">
          <div className="card-head"><div><h3>Layers</h3><p className="subtitle">Derived from path + node type.</p></div><Layers size={16} color="var(--muted-dark)" /></div>
          <div className="dense-list" style={{ maxHeight: 200 }}>
            {layers.length ? layers.map((layer) => (
              <span key={layer.id}>
                <b>{layer.nodeIds.length}</b>{layer.name}
              </span>
            )) : <em>No layers — build the graph.</em>}
          </div>
        </section>
        <section className="glass-card col-4">
          <div className="card-head"><div><h3>Top connected</h3><p className="subtitle">Hubs by combined degree.</p></div><Code2 size={16} color="var(--muted-dark)" /></div>
          <div className="dense-list" style={{ maxHeight: 200 }}>
            {derivation.topConnected.length ? derivation.topConnected.slice(0, 6).map((n) => (
              <span key={n.id}><b>{n.type}</b>{n.qualified_name}</span>
            )) : <em>No edges resolved.</em>}
          </div>
        </section>
        <section className="glass-card col-4">
          <div className="card-head"><div><h3>Inspect raw</h3><p className="subtitle">Verify backend payload.</p></div><ArrowRight size={16} color="var(--primary-coral-bright)" /></div>
          <div className="actions-stack">
            <button className="action-row" onClick={() => window.open("/api/graph", "_blank")}>
              <span className="lead"><ExternalLink size={14} className="ico muted" /> /api/graph</span>
              <span className="chev">→</span>
            </button>
            <button className="action-row" onClick={() => window.open("/api/review", "_blank")}>
              <span className="lead"><ExternalLink size={14} className="ico muted" /> /api/review</span>
              <span className="chev">→</span>
            </button>
          </div>
        </section>
      </section>
    </div>
  );
}
