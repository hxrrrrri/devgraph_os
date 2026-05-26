import clsx from "clsx";
import { ChevronLeft, Search, X, GitPullRequest, Network, Layers, Workflow, Activity, Route, Folder, Compass } from "lucide-react";
import { useDashboardStore, type GraphMode } from "../store/dashboardStore";

const MODES: ReadonlyArray<{ id: GraphMode; label: string; icon: typeof Network }> = [
  { id: "Overview", label: "Overview", icon: Network },
  { id: "Architecture", label: "Architecture", icon: Layers },
  { id: "Impact", label: "Impact", icon: GitPullRequest },
  { id: "Flow", label: "Flow", icon: Workflow },
  { id: "Community", label: "Community", icon: Activity },
];

export function GraphToolbar() {
  const graphMode = useDashboardStore((s) => s.graphMode);
  const setGraphMode = useDashboardStore((s) => s.setGraphMode);
  const navigationLevel = useDashboardStore((s) => s.navigationLevel);
  const activeLayerId = useDashboardStore((s) => s.activeLayerId);
  const layers = useDashboardStore((s) => s.layers);
  const navigateToOverview = useDashboardStore((s) => s.navigateToOverview);
  const searchQuery = useDashboardStore((s) => s.searchQuery);
  const setSearchQuery = useDashboardStore((s) => s.setSearchQuery);
  const diffMode = useDashboardStore((s) => s.diffMode);
  const toggleDiffMode = useDashboardStore((s) => s.toggleDiffMode);
  const changedCount = useDashboardStore((s) => s.changedNodeIds.size);
  const affectedCount = useDashboardStore((s) => s.affectedNodeIds.size);
  const togglePathFinder = useDashboardStore((s) => s.togglePathFinder);
  const toggleFileExplorer = useDashboardStore((s) => s.toggleFileExplorer);
  const pathFinderOpen = useDashboardStore((s) => s.pathFinderOpen);
  const fileExplorerOpen = useDashboardStore((s) => s.fileExplorerOpen);
  const tourActive = useDashboardStore((s) => s.tourActive);
  const startTour = useDashboardStore((s) => s.startTour);
  const stopTour = useDashboardStore((s) => s.stopTour);

  const activeLayerName = layers.find((l) => l.id === activeLayerId)?.name;

  return (
    <div className="graph-toolbar dg-graph-toolbar">
      <div className="mode-tabs">
        {MODES.map((mode) => {
          const Icon = mode.icon;
          return (
            <button
              key={mode.id}
              className={clsx("mode-tab", mode.id === graphMode && "active")}
              onClick={() => setGraphMode(mode.id)}
            >
              <Icon size={13} /> {mode.label}
            </button>
          );
        })}
      </div>
      <div className="dg-toolbar-right">
        {navigationLevel === "layer-detail" && activeLayerName ? (
          <button className="btn btn-secondary btn-tiny" onClick={navigateToOverview}>
            <ChevronLeft size={13} /> Overview · {activeLayerName}
          </button>
        ) : null}
        <button
          className={clsx("btn btn-tiny", diffMode ? "btn-coral-soft" : "btn-secondary")}
          onClick={toggleDiffMode}
          title="Toggle diff overlay (D)"
        >
          <GitPullRequest size={13} /> diff · {changedCount}/{affectedCount}
        </button>
        <button
          className={clsx("btn btn-tiny", pathFinderOpen ? "btn-coral-soft" : "btn-secondary")}
          onClick={togglePathFinder}
          title="Path finder (P)"
        >
          <Route size={13} /> path
        </button>
        <button
          className={clsx("btn btn-tiny", fileExplorerOpen ? "btn-coral-soft" : "btn-secondary")}
          onClick={toggleFileExplorer}
          title="File explorer (F)"
        >
          <Folder size={13} /> files
        </button>
        <button
          className={clsx("btn btn-tiny", tourActive ? "btn-coral-soft" : "btn-secondary")}
          onClick={() => (tourActive ? stopTour() : startTour())}
          title="Guided tour (T)"
        >
          <Compass size={13} /> tour
        </button>
        <label className="search dg-toolbar-search">
          <Search size={13} />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="search graph…"
          />
          {searchQuery ? (
            <button className="icon-button" onClick={() => setSearchQuery("")} aria-label="Clear search">
              <X size={12} />
            </button>
          ) : null}
        </label>
      </div>
    </div>
  );
}
