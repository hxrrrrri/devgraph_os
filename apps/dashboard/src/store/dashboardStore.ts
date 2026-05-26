import { create } from "zustand";
import type { GraphNode, GraphPayload, GraphStatus, ReviewResult } from "@devgraph/schema";

export type GraphMode = "Overview" | "Architecture" | "Impact" | "Flow" | "Community" | "Focused";
export type NavigationLevel = "overview" | "layer-detail";
export type Persona = "junior" | "senior" | "reviewer" | "architect" | "ai-agent";

const MAX_HISTORY = 50;

export type LayerId = string;

export interface DerivedLayer {
  id: LayerId;
  name: string;
  description: string;
  color: string;
  nodeIds: string[];
  stats: {
    files: number;
    symbols: number;
    tests: number;
    docs: number;
  };
}

export interface DashboardStoreState {
  // Server-fed data
  graph: GraphPayload;
  status: GraphStatus | null;
  review: ReviewResult | null;
  memories: Array<{ id: string; kind: string; content: string; created_at?: string }>;

  // Derived indexes (rebuilt by setGraph / setLayers)
  nodesById: Map<string, GraphNode>;
  nodeIdToLayerId: Map<string, LayerId>;
  layers: DerivedLayer[];

  // Selection / focus
  selectedNodeId: string | null;
  focusedNodeId: string | null;
  nodeHistory: string[];

  // Search
  searchQuery: string;
  searchResults: GraphNode[];

  // Graph modes + filters
  graphMode: GraphMode;
  nodeTypeFilters: Set<string>;
  edgeTypeFilters: Set<string>;
  confidenceFilters: Set<string>;

  // Diff overlay
  diffMode: boolean;
  changedNodeIds: Set<string>;
  affectedNodeIds: Set<string>;

  // Path finder result highlight
  pathHighlightIds: Set<string>;

  // Per-file changed-line sets, derived from review.changed_hunks for CodeViewer.
  changedLinesByFile: Map<string, Set<number>>;

  // Layer drill / containers
  navigationLevel: NavigationLevel;
  activeLayerId: LayerId | null;
  expandedContainers: Set<string>;
  containerLayoutCache: Map<string, { childPositions: Map<string, { x: number; y: number }>; size: { width: number; height: number } }>;

  // Layout debug
  layoutIssues: Array<{ level: "info" | "warning" | "error"; message: string }>;

  // Panels
  codeViewerOpen: boolean;
  codeViewerNodeId: string | null;
  codeViewerExpanded: boolean;
  pathFinderOpen: boolean;
  fileExplorerOpen: boolean;
  commandPaletteOpen: boolean;

  // Onboarding
  tourActive: boolean;
  tourStep: number;
  persona: Persona;

  // Actions — data
  setStatus: (status: GraphStatus | null) => void;
  setGraph: (graph: GraphPayload) => void;
  setReview: (review: ReviewResult | null) => void;
  setMemories: (memories: DashboardStoreState["memories"]) => void;
  setLayers: (layers: DerivedLayer[]) => void;

  // Actions — selection
  selectNode: (nodeId: string | null) => void;
  setFocusedNode: (nodeId: string | null) => void;
  goBackNode: () => void;

  // Actions — search
  setSearchQuery: (query: string) => void;
  setSearchResults: (results: GraphNode[]) => void;

  // Actions — modes/filters
  setGraphMode: (mode: GraphMode) => void;
  toggleNodeTypeFilter: (type: string) => void;
  toggleEdgeTypeFilter: (type: string) => void;
  toggleConfidenceFilter: (tier: string) => void;
  resetFilters: () => void;

  // Actions — diff
  setDiffOverlay: (changed: string[], affected: string[]) => void;
  toggleDiffMode: () => void;
  clearDiffOverlay: () => void;

  // Actions — path highlight
  setPathHighlight: (ids: string[]) => void;
  clearPathHighlight: () => void;

  // Actions — layer drill
  drillIntoLayer: (layerId: LayerId) => void;
  navigateToOverview: () => void;
  toggleContainer: (containerId: string) => void;
  setContainerLayout: (
    containerId: string,
    childPositions: Map<string, { x: number; y: number }>,
    size: { width: number; height: number }
  ) => void;
  clearContainerLayouts: () => void;

  // Actions — panels
  openCodeViewer: (nodeId: string) => void;
  closeCodeViewer: () => void;
  toggleCodeViewerExpanded: () => void;
  togglePathFinder: () => void;
  toggleFileExplorer: () => void;
  setCommandPaletteOpen: (open: boolean) => void;

  // Actions — onboarding
  startTour: () => void;
  stopTour: () => void;
  nextTourStep: () => void;
  prevTourStep: () => void;
  setPersona: (persona: Persona) => void;

  // Actions — layout issues
  appendLayoutIssues: (issues: DashboardStoreState["layoutIssues"]) => void;
  clearLayoutIssues: () => void;
}

function rebuildIndexes(graph: GraphPayload, layers: DerivedLayer[]) {
  const nodesById = new Map<string, GraphNode>();
  for (const node of graph.nodes) nodesById.set(node.id, node);
  const nodeIdToLayerId = new Map<string, LayerId>();
  for (const layer of layers) {
    for (const nid of layer.nodeIds) {
      if (!nodeIdToLayerId.has(nid)) nodeIdToLayerId.set(nid, layer.id);
    }
  }
  return { nodesById, nodeIdToLayerId };
}

export const useDashboardStore = create<DashboardStoreState>()((set, get) => ({
  graph: { nodes: [], edges: [] },
  status: null,
  review: null,
  memories: [],

  nodesById: new Map(),
  nodeIdToLayerId: new Map(),
  layers: [],

  selectedNodeId: null,
  focusedNodeId: null,
  nodeHistory: [],

  searchQuery: "",
  searchResults: [],

  graphMode: "Overview",
  nodeTypeFilters: new Set<string>(),
  edgeTypeFilters: new Set<string>(),
  confidenceFilters: new Set<string>(),

  diffMode: false,
  changedNodeIds: new Set<string>(),
  affectedNodeIds: new Set<string>(),

  pathHighlightIds: new Set<string>(),

  changedLinesByFile: new Map<string, Set<number>>(),

  navigationLevel: "overview",
  activeLayerId: null,
  expandedContainers: new Set<string>(),
  containerLayoutCache: new Map(),

  layoutIssues: [],

  codeViewerOpen: false,
  codeViewerNodeId: null,
  codeViewerExpanded: false,
  pathFinderOpen: false,
  fileExplorerOpen: false,
  commandPaletteOpen: false,

  tourActive: false,
  tourStep: 0,
  persona: "junior",

  setStatus: (status) => set({ status }),
  setGraph: (graph) => {
    const { layers } = get();
    const { nodesById, nodeIdToLayerId } = rebuildIndexes(graph, layers);
    set({
      graph,
      nodesById,
      nodeIdToLayerId,
      // Reset transient state — selection ids may have been removed.
      selectedNodeId: null,
      focusedNodeId: null,
      nodeHistory: [],
      expandedContainers: new Set(),
      containerLayoutCache: new Map(),
    });
  },
  setReview: (review) => {
    const changedLinesByFile = new Map<string, Set<number>>();
    if (review) {
      for (const raw of review.changed_hunks ?? []) {
        const hunk = raw as { file_path?: unknown; changed_lines?: unknown; new_start?: unknown; new_count?: unknown };
        const filePath = typeof hunk.file_path === "string" ? hunk.file_path : null;
        if (!filePath) continue;
        const set = changedLinesByFile.get(filePath) ?? new Set<number>();
        if (Array.isArray(hunk.changed_lines)) {
          for (const line of hunk.changed_lines) {
            if (typeof line === "number") set.add(line);
          }
        } else if (typeof hunk.new_start === "number") {
          const start = hunk.new_start;
          const count = typeof hunk.new_count === "number" ? hunk.new_count : 1;
          for (let i = 0; i < count; i++) set.add(start + i);
        }
        changedLinesByFile.set(filePath, set);
      }
    }
    set({ review, changedLinesByFile });
    if (review) {
      get().setDiffOverlay(
        review.changed_nodes.map((node) => node.id),
        review.impacted_nodes.map((node) => node.id)
      );
    }
  },
  setMemories: (memories) => set({ memories }),
  setLayers: (layers) => {
    const { graph } = get();
    const { nodesById, nodeIdToLayerId } = rebuildIndexes(graph, layers);
    set({ layers, nodesById, nodeIdToLayerId });
  },

  selectNode: (nodeId) => {
    const { selectedNodeId, nodeHistory } = get();
    if (nodeId && selectedNodeId && nodeId !== selectedNodeId) {
      set({ selectedNodeId: nodeId, nodeHistory: [...nodeHistory, selectedNodeId].slice(-MAX_HISTORY) });
    } else {
      set({ selectedNodeId: nodeId });
    }
  },
  setFocusedNode: (nodeId) =>
    set({
      focusedNodeId: nodeId,
      selectedNodeId: nodeId,
      // Focus narrows visible nodes; cached child positions may reference filtered-out ids.
      expandedContainers: new Set(),
      containerLayoutCache: new Map(),
    }),
  goBackNode: () => {
    const { nodeHistory } = get();
    if (nodeHistory.length === 0) return;
    const prev = nodeHistory[nodeHistory.length - 1];
    set({ selectedNodeId: prev, nodeHistory: nodeHistory.slice(0, -1) });
  },

  setSearchQuery: (query) => set({ searchQuery: query }),
  setSearchResults: (results) => set({ searchResults: results }),

  setGraphMode: (mode) =>
    set({
      graphMode: mode,
      // Mode switch invalidates layout cache.
      expandedContainers: new Set(),
      containerLayoutCache: new Map(),
    }),
  toggleNodeTypeFilter: (type) =>
    set((state) => {
      const next = new Set(state.nodeTypeFilters);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return { nodeTypeFilters: next, containerLayoutCache: new Map(), expandedContainers: new Set() };
    }),
  toggleEdgeTypeFilter: (type) =>
    set((state) => {
      const next = new Set(state.edgeTypeFilters);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return { edgeTypeFilters: next };
    }),
  toggleConfidenceFilter: (tier) =>
    set((state) => {
      const next = new Set(state.confidenceFilters);
      if (next.has(tier)) next.delete(tier);
      else next.add(tier);
      return { confidenceFilters: next };
    }),
  resetFilters: () =>
    set({ nodeTypeFilters: new Set(), edgeTypeFilters: new Set(), confidenceFilters: new Set() }),

  setDiffOverlay: (changed, affected) =>
    set({ diffMode: true, changedNodeIds: new Set(changed), affectedNodeIds: new Set(affected) }),
  toggleDiffMode: () => set((state) => ({ diffMode: !state.diffMode })),
  clearDiffOverlay: () => set({ diffMode: false, changedNodeIds: new Set(), affectedNodeIds: new Set() }),

  setPathHighlight: (ids) => set({ pathHighlightIds: new Set(ids) }),
  clearPathHighlight: () => set({ pathHighlightIds: new Set() }),

  drillIntoLayer: (layerId) =>
    set({
      navigationLevel: "layer-detail",
      activeLayerId: layerId,
      selectedNodeId: null,
      focusedNodeId: null,
      // Container ids collide across layers — clear cache to avoid stale positions.
      containerLayoutCache: new Map(),
      expandedContainers: new Set(),
    }),
  navigateToOverview: () =>
    set({
      navigationLevel: "overview",
      activeLayerId: null,
      selectedNodeId: null,
      focusedNodeId: null,
      containerLayoutCache: new Map(),
      expandedContainers: new Set(),
    }),
  toggleContainer: (containerId) =>
    set((state) => {
      const next = new Set(state.expandedContainers);
      if (next.has(containerId)) next.delete(containerId);
      else next.add(containerId);
      return { expandedContainers: next };
    }),
  setContainerLayout: (containerId, childPositions, size) =>
    set((state) => {
      const next = new Map(state.containerLayoutCache);
      next.set(containerId, { childPositions, size });
      return { containerLayoutCache: next };
    }),
  clearContainerLayouts: () => set({ containerLayoutCache: new Map(), expandedContainers: new Set() }),

  openCodeViewer: (nodeId) => set({ codeViewerOpen: true, codeViewerNodeId: nodeId, codeViewerExpanded: false }),
  closeCodeViewer: () => set({ codeViewerOpen: false, codeViewerNodeId: null, codeViewerExpanded: false }),
  toggleCodeViewerExpanded: () => set((state) => ({ codeViewerExpanded: !state.codeViewerExpanded })),
  togglePathFinder: () => set((state) => ({ pathFinderOpen: !state.pathFinderOpen })),
  toggleFileExplorer: () => set((state) => ({ fileExplorerOpen: !state.fileExplorerOpen })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

  startTour: () => set({ tourActive: true, tourStep: 0 }),
  stopTour: () => set({ tourActive: false, tourStep: 0 }),
  nextTourStep: () => set((state) => ({ tourStep: state.tourStep + 1 })),
  prevTourStep: () => set((state) => ({ tourStep: Math.max(0, state.tourStep - 1) })),
  setPersona: (persona) => set({ persona }),

  appendLayoutIssues: (issues) =>
    set((state) => {
      if (issues.length === 0) return {};
      const seen = new Set(state.layoutIssues.map((i) => `${i.level}|${i.message}`));
      const fresh = issues.filter((i) => !seen.has(`${i.level}|${i.message}`));
      if (fresh.length === 0) return {};
      return { layoutIssues: [...state.layoutIssues, ...fresh] };
    }),
  clearLayoutIssues: () => set({ layoutIssues: [] }),
}));
