import {
  Bell,
  BookOpen,
  Boxes,
  Brain,
  Bug,
  Command,
  Compass,
  FileText,
  GitBranch,
  GitPullRequest,
  LayoutDashboard,
  Lightbulb,
  Network,
  Radar,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Terminal,
  TrendingUp,
  Waypoints,
  Workflow,
  type LucideIcon
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import clsx from "clsx";
import type { GraphPayload, GraphStatus, ReviewResult } from "@devgraph/schema";
import { client } from "./api/client";
import { SkeletonCard } from "./components/Skeleton";
import { useDismissible } from "./utils/dismiss";
import { DebugLens } from "./debug/DebugLens";
import { GraphExplorer } from "./graph/GraphExplorer";
import { HandoffLens } from "./handoff/HandoffLens";
import { KnowledgeLens } from "./knowledge/KnowledgeLens";
import { OnboardingLens } from "./onboard/OnboardingLens";
import { ReviewLens } from "./review/ReviewLens";
import { useDashboardStore } from "./store/dashboardStore";
import { GuidedTour } from "./onboard/GuidedTour";
import { deriveArchitecture } from "./graph/graphAdapter";

type Page = "overview" | "graph" | "review" | "debug" | "onboard" | "knowledge" | "flows" | "handoff";
type Memory = { id: string; kind: string; content: string; created_at?: string };

const navItems: Array<{ id: Page; label: string; icon: LucideIcon }> = [
  { id: "overview", label: "Command", icon: LayoutDashboard },
  { id: "graph", label: "Graph", icon: Network },
  { id: "review", label: "Review", icon: GitPullRequest },
  { id: "debug", label: "Debug", icon: Bug },
  { id: "flows", label: "Flows", icon: Waypoints },
  { id: "knowledge", label: "Knowledge", icon: Brain },
  { id: "onboard", label: "Onboard", icon: BookOpen },
  { id: "handoff", label: "Handoff", icon: Send }
];

const stagger = {
  show: { transition: { staggerChildren: 0.06 } }
};
const rise = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.42, ease: [0.22, 1, 0.36, 1] } }
};

export function App() {
  const [page, setPage] = useState<Page>("overview");
  const [status, setStatus] = useState<GraphStatus | null>(null);
  const [graph, setGraph] = useState<GraphPayload>({ nodes: [], edges: [] });
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [search, setSearch] = useState("");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const storeSetGraph = useDashboardStore((s) => s.setGraph);
  const storeSetStatus = useDashboardStore((s) => s.setStatus);
  const storeSetReview = useDashboardStore((s) => s.setReview);
  const storeSetMemories = useDashboardStore((s) => s.setMemories);
  const togglePathFinder = useDashboardStore((s) => s.togglePathFinder);
  const toggleFileExplorer = useDashboardStore((s) => s.toggleFileExplorer);
  const toggleDiffMode = useDashboardStore((s) => s.toggleDiffMode);
  const tourActive = useDashboardStore((s) => s.tourActive);
  const startTour = useDashboardStore((s) => s.startTour);
  const stopTour = useDashboardStore((s) => s.stopTour);

  async function refresh() {
    try {
      setLoading(true);
      setError(null);
      const [nextStatus, nextGraph, nextReview, memoryPayload] = await Promise.allSettled([
        client.status(),
        client.graph(),
        client.review(),
        client.memories()
      ]);
      if (nextStatus.status === "fulfilled") {
        setStatus(nextStatus.value);
        storeSetStatus(nextStatus.value);
      }
      if (nextGraph.status === "fulfilled") {
        setGraph(nextGraph.value);
        storeSetGraph(nextGraph.value);
      }
      if (nextReview.status === "fulfilled") {
        setReview(nextReview.value);
        storeSetReview(nextReview.value);
      }
      if (memoryPayload.status === "fulfilled") {
        const payload = memoryPayload.value as { memories?: Memory[] };
        const next = payload.memories ?? [];
        setMemories(next);
        storeSetMemories(next);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load DevGraph data");
    } finally {
      setLoading(false);
    }
  }

  async function loadReview() {
    try {
      const nextReview = await client.review();
      setReview(nextReview);
      storeSetReview(nextReview);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load review data");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const inEditable = target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((value) => !value);
        return;
      }
      if (event.key === "Escape" && paletteOpen) {
        setPaletteOpen(false);
        return;
      }
      if (inEditable || paletteOpen) return;
      if (event.key === "j" || event.key === "k") {
        event.preventDefault();
        setPage((current) => {
          const idx = navItems.findIndex((item) => item.id === current);
          const next = event.key === "j" ? idx + 1 : idx - 1;
          const safe = (next + navItems.length) % navItems.length;
          return navItems[safe].id;
        });
      }
      if (event.key === "p" || event.key === "P") {
        event.preventDefault();
        togglePathFinder();
      }
      if (event.key === "f" || event.key === "F") {
        event.preventDefault();
        toggleFileExplorer();
      }
      if (event.key === "d" || event.key === "D") {
        event.preventDefault();
        toggleDiffMode();
      }
      if (event.key === "t" || event.key === "T") {
        event.preventDefault();
        if (tourActive) stopTour();
        else startTour();
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [paletteOpen, togglePathFinder, toggleFileExplorer, toggleDiffMode, tourActive, startTour, stopTour]);

  const paletteResults = useMemo(() => {
    const query = paletteQuery.trim().toLowerCase();
    if (!query) {
      return { commands: navItems, nodes: [] as typeof graph.nodes };
    }
    const commands = navItems.filter((item) => item.label.toLowerCase().includes(query) || item.id.includes(query));
    const nodes = graph.nodes
      .filter((node) => node.qualified_name.toLowerCase().includes(query) || node.name.toLowerCase().includes(query))
      .slice(0, 8);
    return { commands, nodes };
  }, [paletteQuery, graph.nodes]);

  const filteredGraph = useMemo(() => {
    if (!search.trim()) return graph;
    const term = search.toLowerCase();
    const nodes = graph.nodes.filter((node) => node.qualified_name.toLowerCase().includes(term) || node.type.includes(term));
    const ids = new Set(nodes.map((node) => node.id));
    return {
      nodes,
      edges: graph.edges.filter((edge) => ids.has(edge.source_id) && ids.has(edge.target_id))
    };
  }, [graph, search]);

  const fresh = Boolean(status?.last_indexed_at);

  return (
    <div className="app-shell">
      <aside className="rail" aria-label="DevGraph navigation">
        <div className="rail-logo">DG</div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={clsx("rail-button", page === item.id && "active")}
              onClick={() => setPage(item.id)}
              title={item.label}
            >
              <Icon size={19} strokeWidth={1.6} />
            </button>
          );
        })}
        <div className="rail-spacer" />
        <button className="rail-button" title="Refresh" onClick={() => void refresh()}>
          <RefreshCw size={18} strokeWidth={1.6} />
        </button>
      </aside>

      <header className="topbar">
        <div className="topbar-brand">
          <span className="mark">DevGraph OS</span>
          <span className="divider" />
          <span className="project">{status?.project ?? "local graph"}</span>
        </div>
        <label className="search">
          <Search size={15} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search knowledge graph…"
          />
          <kbd>⌘K</kbd>
        </label>
        <div className="topbar-actions">
          <span className="local-badge"><ShieldCheck size={11} /> local-first</span>
          <span className={clsx("branch-pill", !fresh && "stale")}>
            <span className="dot" />
            {fresh ? "main branch" : "stale graph"}
          </span>
          <button className="icon-button" onClick={() => void refresh()} title="Refresh">
            <RefreshCw size={16} />
          </button>
          <button className="icon-button" onClick={() => setPaletteOpen(true)} title="Command palette (⌘K)">
            <Terminal size={16} />
          </button>
          <button className="icon-button" title="Notifications">
            <Bell size={16} />
          </button>
        </div>
      </header>

      <main className="main">
        {error ? <div className="alert"><Sparkles size={14} /> {error}</div> : null}

        <AnimatePresence mode="wait">
          <motion.section
            key={page}
            className="page-frame"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          >
            {page === "overview" ? (
              loading && !status ? (
                <section className="kpi-grid">
                  {Array.from({ length: 4 }).map((_, idx) => <SkeletonCard key={idx} />)}
                </section>
              ) : (
                <Overview
                  status={status}
                  graph={graph}
                  review={review}
                  memories={memories}
                  onReview={() => void loadReview()}
                  setPage={setPage}
                />
              )
            ) : null}
            {page === "graph" ? <GraphExplorer /> : null}
            {page === "review" ? <ReviewLens review={review} onLoadReview={() => void loadReview()} /> : null}
            {page === "debug" ? <DebugLens graph={filteredGraph} /> : null}
            {page === "onboard" ? <OnboardingLens status={status} graph={graph} /> : null}
            {page === "knowledge" ? <KnowledgeLens graph={filteredGraph} /> : null}
            {page === "flows" ? <FlowLens graph={filteredGraph} /> : null}
            {page === "handoff" ? <HandoffLens /> : null}
          </motion.section>
        </AnimatePresence>
      </main>

      <footer className="footer-bar">
        <span>© DevGraph OS · System status: {fresh ? "optimal" : "stale"}</span>
        <div className="links">
          <a href="https://github.com/hxrrrrri/devgraph_os" target="_blank" rel="noreferrer">GitHub</a>
          <a href="/api/status" target="_blank" rel="noreferrer">API</a>
          <a href="https://github.com/hxrrrrri/devgraph_os/blob/main/CHANGELOG.md" target="_blank" rel="noreferrer">Changelog</a>
        </div>
      </footer>

      <GuidedTour
        onCta={(action) => {
          if (action === "openReview") setPage("review");
          else if (action === "openHandoff") setPage("handoff");
          else if (action === "overview") setPage("graph");
        }}
      />

      {paletteOpen ? (
        <div className="palette-backdrop" onClick={() => setPaletteOpen(false)}>
          <div className="palette" onClick={(event) => event.stopPropagation()}>
            <div className="palette-head"><Command size={14} /> Commands</div>
            <input
              autoFocus
              className="palette-input"
              placeholder="Search commands, nodes, files…"
              value={paletteQuery}
              onChange={(event) => setPaletteQuery(event.target.value)}
            />
            {paletteResults.commands.map((item) => (
              <button key={item.id} onClick={() => { setPage(item.id); setPaletteOpen(false); setPaletteQuery(""); }}>
                <item.icon size={15} />
                <span>{item.label}</span>
              </button>
            ))}
            {paletteResults.nodes.length ? <div className="palette-section">Nodes</div> : null}
            {paletteResults.nodes.map((node) => (
              <button
                key={node.id}
                onClick={() => { setPage("graph"); setSearch(node.qualified_name); setPaletteOpen(false); setPaletteQuery(""); }}
              >
                <Network size={15} />
                <span>{node.qualified_name}</span>
                <small>{node.type}</small>
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Overview({
  status,
  graph,
  review,
  memories,
  onReview,
  setPage
}: {
  status: GraphStatus | null;
  graph: GraphPayload;
  review: ReviewResult | null;
  memories: Memory[];
  onReview: () => void;
  setPage: (page: Page) => void;
}) {
  const confidenceRows = Object.entries(countBy(graph.nodes.map((node) => node.confidence_tier))).map(
    ([name, value]) => ({ name, value })
  );
  const typeRows = Object.entries(countBy(graph.nodes.map((node) => node.type))).sort((a, b) => b[1] - a[1]);
  const languageRows = Object.entries(status?.languages ?? {}).sort((a, b) => b[1] - a[1]);
  const projectName = status?.project ?? "DevGraph Core";
  const lastIndexed = status?.last_indexed_at ? formatRelative(status.last_indexed_at) : "never";
  const warnings = status?.warnings.length ?? 0;
  const riskLevel = review?.risk_level ?? "low";
  const riskScore = review?.risk_score ?? 0;

  const activity = useMemo(() => buildActivity({ status, review, memories }), [status, review, memories]);
  const radarSectors = useMemo(() => buildRadar(review), [review]);
  const architecture = useMemo(() => deriveArchitecture(graph), [graph]);

  return (
    <motion.div variants={stagger} initial="hidden" animate="show" style={{ display: "grid", gap: 22 }}>
      {/* Hero card */}
      <motion.section className="hero-card" variants={rise}>
        <div style={{ position: "relative", zIndex: 1, minWidth: 0 }}>
          <span className="page-eyebrow">
            project overview <span className="rule" />
            <span style={{ color: status?.last_indexed_at ? "var(--accent-teal)" : "var(--accent-amber)" }}>
              {status?.last_indexed_at ? "synchronized" : "needs build"}
            </span>
          </span>
          <h1 className="page-title" style={{ marginTop: 12 }}>{projectName}</h1>
          <div className="hero-meta">
            <span className="chip"><GitBranch size={14} /> branch: main</span>
            <span className="chip"><RefreshCw size={14} /> updated {lastIndexed}</span>
            <span className="chip"><FileText size={14} /> {status?.total_files ?? 0} files</span>
          </div>
        </div>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={() => setPage("review")}>
            <Sparkles size={14} /> Quick actions
          </button>
          <button className="btn btn-secondary" onClick={() => setPage("graph")}>
            <Network size={14} /> View graph
          </button>
        </div>
      </motion.section>

      {/* KPI cards */}
      <motion.section className="kpi-grid" variants={stagger}>
        <KpiCard icon={FileText} label="Files indexed" value={status?.total_files ?? 0} trend={status?.total_files ? "+ live" : "build needed"} tone={status?.total_files ? "up" : "warn"} />
        <KpiCard icon={Boxes} label="Graph nodes" value={status?.total_nodes ?? 0} trend="entities" />
        <KpiCard icon={Workflow} label="Edges" value={status?.total_edges ?? 0} trend="connections" />
        <KpiCard
          icon={ShieldCheck}
          label="Risk score"
          value={riskScore}
          suffix="/100"
          trend={riskLevel}
          tone={riskLevel === "critical" || riskLevel === "high" ? "crit" : riskLevel === "medium" ? "warn" : "up"}
        />
      </motion.section>

      {/* Bento row 1: pulse + radar */}
      <motion.div className="bento" variants={stagger}>
        <motion.section className="glass-card pulse-panel col-8" variants={rise}>
          <div className="card-head">
            <div>
              <h3>Intelligence pulse</h3>
              <p className="subtitle">Real-time connection mapping across the active graph.</p>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <span className="dot" style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--primary-coral-bright)", boxShadow: "0 0 8px var(--primary-coral-glow)", animation: "pulse-soft 2s infinite" }} />
              <span style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--accent-teal)", boxShadow: "0 0 8px var(--accent-teal)" }} />
            </div>
          </div>
          <div className="pulse-canvas">
            <PulseSvg graph={graph} />
            <div className="pulse-overlay">
              <span className="card-label">live datastream</span>
              <span className="stream">{graph.nodes[0]?.qualified_name ?? "no nodes — run `devgraph build`"}</span>
            </div>
          </div>
        </motion.section>

        <motion.section className="glass-card col-4" variants={rise}>
          <div className="card-head">
            <div>
              <h3>Risk radar</h3>
              <p className="subtitle">Architectural vulnerability vectors.</p>
            </div>
            <Radar size={16} color="var(--muted-dark)" />
          </div>
          <div className="radar">
            <span className="label top">API</span>
            <span className="label right">Logic</span>
            <span className="label bottom">Auth</span>
            <span className="label left">Database</span>
            <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
              <polygon
                points={radarSectors.map((p) => `${p.x},${p.y}`).join(" ")}
                fill="rgba(124, 215, 196, 0.18)"
                stroke="var(--accent-teal)"
                strokeWidth="1"
              />
              {radarSectors.map((p, i) => (
                <circle key={i} cx={p.x} cy={p.y} r="1.8" fill="var(--on-dark)" />
              ))}
            </svg>
          </div>
          <div className="gauge-meta" style={{ marginTop: 18 }}>
            {radarSectors.map((sector) => (
              <div key={sector.label}>
                <div className="meta-row">
                  <span className="label">{sector.label}</span>
                  <span className={`level ${sector.level}`}>{sector.level}</span>
                </div>
                <div className={`meta-bar ${sector.level}`}>
                  <i style={{ width: `${sector.pct}%`, background: sector.level === "low" ? "var(--accent-teal)" : sector.level === "medium" ? "var(--accent-amber)" : "var(--error)" }} />
                </div>
              </div>
            ))}
          </div>
        </motion.section>
      </motion.div>

      {/* Architecture snapshot: layer load + top hubs */}
      <motion.div className="bento" variants={stagger}>
        <motion.section className="glass-card col-7" variants={rise}>
          <div className="card-head">
            <div>
              <h3>Architecture snapshot</h3>
              <p className="subtitle">{architecture.layers.length} layers · derived from path + node type. Click "open architecture overview" to drill in.</p>
            </div>
            <button className="btn btn-secondary" onClick={() => setPage("graph")}>
              <Network size={14} /> Open architecture overview
            </button>
          </div>
          <div className="dg-arch-grid">
            {architecture.layers.length ? architecture.layers.map((layer) => (
              <button key={layer.id} className="dg-arch-card" onClick={() => setPage("graph")}>
                <span className="dg-arch-bar" style={{ background: layer.color }} />
                <span className="dg-arch-name">{layer.name}</span>
                <span className="dg-arch-stats">
                  <b>{layer.nodeIds.length}</b> nodes · {layer.stats.symbols} symbols · {layer.stats.tests} tests
                </span>
              </button>
            )) : <em style={{ color: "var(--muted-dark)" }}>No layers — run <code>devgraph build</code>.</em>}
          </div>
        </motion.section>

        <motion.section className="glass-card col-5" variants={rise}>
          <div className="card-head"><div><h3>Top connected nodes</h3><p className="subtitle">Hubs by combined degree.</p></div></div>
          <div className="dense-list" style={{ maxHeight: 240 }}>
            {architecture.topConnected.length ? architecture.topConnected.slice(0, 8).map((node) => (
              <span key={node.id}><b>{node.type}</b>{node.qualified_name}</span>
            )) : <em style={{ color: "var(--muted-dark)" }}>No edges resolved yet.</em>}
          </div>
        </motion.section>
      </motion.div>

      {/* Bento row 2: activity + best actions */}
      <motion.div className="bento" variants={stagger}>
        <motion.section className="glass-card col-7" variants={rise}>
          <div className="card-head">
            <div>
              <h3>Recent activity</h3>
              <p className="subtitle">Build, review, and memory events.</p>
            </div>
            <button className="btn btn-ghost" onClick={() => setPage("handoff")}>View all</button>
          </div>
          <div className="timeline">
            {activity.length ? activity.map((row) => (
              <div key={row.key} className={clsx("timeline-row", row.tone)}>
                <span className="dot" />
                <div>
                  <span className="title">{row.title}</span>
                  <span className="sub">{row.subtitle}</span>
                </div>
                <time>{row.time}</time>
              </div>
            )) : <em style={{ color: "var(--muted-dark)" }}>No activity yet. Run <code>devgraph build</code>.</em>}
          </div>
        </motion.section>

        <motion.section className="glass-card col-5" variants={rise}>
          <div className="card-head">
            <div>
              <h3>Best actions</h3>
              <p className="subtitle">Next moves based on graph state.</p>
            </div>
          </div>
          <div className="actions-stack">
            <ActionRow icon={GitPullRequest} tone="coral" label="Review changes" onClick={() => { onReview(); setPage("review"); }} />
            <ActionRow icon={Sparkles} tone="teal" label="Explain top hotspot" onClick={() => setPage("graph")} />
            <ActionRow icon={Compass} tone="muted" label="Open graph explorer" onClick={() => setPage("graph")} />
            <ActionRow icon={Send} tone="muted" label="Prepare handoff" onClick={() => setPage("handoff")} />
          </div>
          <ProTip />
        </motion.section>
      </motion.div>

      {/* Bento row 3: confidence + hotspots */}
      <motion.div className="bento" variants={stagger}>
        <motion.section className="glass-card col-4" variants={rise}>
          <div className="card-head"><div><h3>Confidence mix</h3><p className="subtitle">Extracted vs inferred vs LLM vs user.</p></div></div>
          <div className="confidence-grid">
            {confidenceRows.length ? confidenceRows.map((row) => (
              <div key={row.name} className={`confidence-cell ${row.name}`}>
                <span className="key">{row.name}</span>
                <span className="val">{row.value}</span>
              </div>
            )) : <em style={{ color: "var(--muted-dark)" }}>No graph nodes yet.</em>}
          </div>
        </motion.section>

        <motion.section className="glass-card col-4" variants={rise}>
          <div className="card-head"><div><h3>Top node types</h3><p className="subtitle">Distribution across graph.</p></div></div>
          <div className="dense-list" style={{ maxHeight: 260 }}>
            {typeRows.length ? typeRows.slice(0, 8).map(([name, value]) => (
              <span key={name}><b>{value}</b>{name}</span>
            )) : <em>No graph nodes yet.</em>}
          </div>
        </motion.section>

        <motion.section className="glass-card col-4" variants={rise}>
          <div className="card-head"><div><h3>Languages</h3><p className="subtitle">Files per language.</p></div></div>
          <div className="dense-list" style={{ maxHeight: 260 }}>
            {languageRows.length ? languageRows.slice(0, 8).map(([name, value]) => (
              <span key={name}><b>{value}</b>{name}</span>
            )) : <em>No language stats yet.</em>}
          </div>
        </motion.section>
      </motion.div>

      {/* Bento row 4: memories + health */}
      <motion.div className="bento" variants={stagger}>
        <motion.section className="glass-card col-7" variants={rise}>
          <div className="card-head"><div><h3>Memories & sessions</h3><p className="subtitle">Notes the agent carries across handoffs.</p></div><Brain size={16} color="var(--knowledge-violet)" /></div>
          <div className="timeline">
            {memories.length ? memories.slice(0, 5).map((memory) => (
              <div key={memory.id} className="timeline-row muted">
                <span className="dot" />
                <div>
                  <span className="title">{memory.kind}</span>
                  <span className="sub">{memory.content}</span>
                </div>
                <time>{memory.created_at ? formatRelative(memory.created_at) : ""}</time>
              </div>
            )) : <em style={{ color: "var(--muted-dark)" }}>No memories yet. Save one with <code>devgraph remember "…"</code>.</em>}
          </div>
        </motion.section>

        <motion.section className="glass-card col-5" variants={rise}>
          <div className="card-head"><div><h3>System health</h3><p className="subtitle">Quick green/amber roll-up.</p></div></div>
          <div className="health-strip">
            <span className={clsx("health-pill", (status?.total_nodes ?? 0) === 0 && "warn")}>Graph</span>
            <span className={clsx("health-pill", (status?.total_chunks ?? 0) === 0 && "warn")}>Chunks</span>
            <span className={clsx("health-pill", !review && "warn")}>Review</span>
            <span className={clsx("health-pill", warnings > 0 && "warn")}>Warnings</span>
          </div>
          {warnings > 0 && status ? (
            <div className="dense-list" style={{ marginTop: 16 }}>
              {status.warnings.slice(0, 4).map((warning) => (
                <span key={warning} className="attention"><b>warn</b>{warning}</span>
              ))}
            </div>
          ) : null}
        </motion.section>
      </motion.div>
    </motion.div>
  );
}

function FlowLens({ graph }: { graph: GraphPayload }) {
  const flowEdges = graph.edges
    .filter((edge) => ["calls", "routes_to", "reads_from", "writes_to", "depends_on"].includes(edge.type))
    .slice(0, 36);
  const byId = new Map(graph.nodes.map((node) => [node.id, node]));
  return (
    <div style={{ display: "grid", gap: 22 }}>
      <header>
        <span className="page-eyebrow">flow lens <span className="rule" /> execution + data paths</span>
        <h1 className="page-title" style={{ marginTop: 10 }}>Flows</h1>
        <p className="page-subtitle">Calls, routes, reads, writes and dependencies across the live graph.</p>
      </header>
      <section className="bento">
        <section className="glass-card col-8">
          <div className="card-head"><div><h3>Flow chains</h3><p className="subtitle">{flowEdges.length} edges in current view.</p></div></div>
          <div className="flow-list">
            {flowEdges.length ? flowEdges.map((edge) => (
              <div key={edge.id}>
                <span>{byId.get(edge.source_id)?.qualified_name ?? edge.source_id}</span>
                <b>{edge.type}</b>
                <span>{byId.get(edge.target_id)?.qualified_name ?? edge.target_id}</span>
              </div>
            )) : <em style={{ color: "var(--muted-dark)" }}>No flow edges in the current graph view.</em>}
          </div>
        </section>
        <section className="glass-card col-4">
          <div className="card-head"><div><h3>Signal pulse</h3><p className="subtitle">Visual heartbeat of active edges.</p></div></div>
          <div className="flow-pulse" />
          <p className="subtitle" style={{ marginTop: 14 }}>
            Pulse intensity scales with edges resolved through tree-sitter — drop sharply if graph drifts.
          </p>
        </section>
      </section>
    </div>
  );
}

function KpiCard({ icon: Icon, label, value, suffix = "", trend, tone }: { icon: LucideIcon; label: string; value: number; suffix?: string; trend?: string; tone?: "up" | "warn" | "crit" }) {
  return (
    <motion.section className="kpi" variants={rise} whileHover={{ y: -3 }} transition={{ duration: 0.18 }}>
      <div className="kpi-head">
        <span className="kpi-label">{label}</span>
        <span className="kpi-icon"><Icon size={16} /></span>
      </div>
      <span className="kpi-value">
        <CountUp to={value} suffix={suffix} />
      </span>
      {trend ? (
        <span className={clsx("kpi-trend", tone)}>
          <TrendingUp size={12} /> {trend}
        </span>
      ) : null}
    </motion.section>
  );
}

function ProTip() {
  const { dismissed, dismiss } = useDismissible("overview-pro-tip");
  if (dismissed) return null;
  return (
    <div className="tip" style={{ position: "relative" }}>
      <button
        className="icon-button"
        aria-label="Dismiss tip"
        onClick={dismiss}
        style={{ position: "absolute", top: 6, right: 6, width: 22, height: 22, color: "var(--muted-dark)" }}
      >
        ×
      </button>
      <div className="tip-label"><Lightbulb size={12} /> pro tip</div>
      <p>Press <code>⌘K</code> to jump to any node, file, or lens.</p>
    </div>
  );
}

function ActionRow({ icon: Icon, tone, label, onClick }: { icon: LucideIcon; tone: "coral" | "teal" | "muted"; label: string; onClick: () => void }) {
  return (
    <button className="action-row" onClick={onClick}>
      <span className="lead">
        <Icon size={16} className={`ico ${tone === "coral" ? "" : tone}`} />
        {label}
      </span>
      <span className="chev">→</span>
    </button>
  );
}

function CountUp({ to, suffix = "" }: { to: number; suffix?: string }) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const duration = 1100;
    const target = Number.isFinite(to) ? to : 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - t) * (1 - t);
      setValue(Math.round(eased * target));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to]);
  return <>{value.toLocaleString()}{suffix}</>;
}

function PulseSvg({ graph }: { graph: GraphPayload }) {
  const sampleNodes = graph.nodes.slice(0, 7);
  const points = sampleNodes.length
    ? sampleNodes.map((_, idx, arr) => ({
        x: 80 + (640 / Math.max(1, arr.length - 1)) * idx,
        y: 200 + Math.sin((idx / arr.length) * Math.PI * 2) * 90,
        accent: idx % 2 === 0 ? "var(--primary-coral-bright)" : "var(--accent-teal)"
      }))
    : [
        { x: 120, y: 230, accent: "var(--primary-coral-bright)" },
        { x: 260, y: 130, accent: "var(--accent-teal)" },
        { x: 410, y: 270, accent: "var(--primary-coral-bright)" },
        { x: 560, y: 150, accent: "var(--accent-teal)" },
        { x: 700, y: 220, accent: "var(--primary-coral-bright)" }
      ];
  const path = points.map((p, idx) => `${idx === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  return (
    <svg viewBox="0 0 800 400" preserveAspectRatio="xMidYMid meet">
      <path d={path} fill="none" stroke="rgba(255, 181, 157, 0.32)" strokeWidth={1.2} className="signal-line" />
      <path
        d={points.slice(1).map((p, idx) => `${idx === 0 ? "M" : "L"} ${points[idx].x} ${points[idx].y} L ${p.x} ${p.y}`).join(" ")}
        fill="none"
        stroke="rgba(124, 215, 196, 0.20)"
        strokeWidth={1}
      />
      {points.map((point, idx) => (
        <circle
          key={idx}
          cx={point.x}
          cy={point.y}
          r={idx % 3 === 0 ? 7 : 4}
          fill={point.accent}
          style={{ filter: `drop-shadow(0 0 ${idx % 3 === 0 ? 12 : 6}px ${point.accent})`, animation: `pulse-soft ${2 + idx * 0.4}s ease-in-out infinite` }}
        />
      ))}
    </svg>
  );
}

type ActivityRow = { key: string; title: string; subtitle: string; time: string; tone: "coral" | "" | "muted" };

function buildActivity({ status, review, memories }: { status: GraphStatus | null; review: ReviewResult | null; memories: Memory[] }): ActivityRow[] {
  const rows: ActivityRow[] = [];
  if (status?.last_indexed_at) {
    rows.push({
      key: "build",
      title: "Graph build successful",
      subtitle: `Indexed ${status.total_files} files into ${status.total_nodes} nodes.`,
      time: formatRelative(status.last_indexed_at),
      tone: "coral"
    });
  }
  if (review) {
    rows.push({
      key: "review",
      title: `Review ${review.risk_level.toUpperCase()} · score ${review.risk_score}`,
      subtitle: `${review.changed_files.length} changed files, ${review.impacted_files.length} impacted, ${review.affected_tests.length} tests touched.`,
      time: "just now",
      tone: ""
    });
  }
  memories.slice(0, 3).forEach((memory) => {
    rows.push({
      key: `memory-${memory.id}`,
      title: `Memory · ${memory.kind}`,
      subtitle: memory.content.length > 120 ? `${memory.content.slice(0, 117)}…` : memory.content,
      time: memory.created_at ? formatRelative(memory.created_at) : "stored",
      tone: "muted"
    });
  });
  return rows;
}

function buildRadar(review: ReviewResult | null) {
  const labels = ["API", "Logic", "Auth", "Database"] as const;
  const baseScore = review?.risk_score ?? 0;
  const apiScore = Math.min(100, baseScore + (review?.public_api_changes.length ?? 0) * 8 + (review?.route_contract_changes.length ?? 0) * 6);
  const logicScore = Math.min(100, baseScore + (review?.changed_symbols.length ?? 0) * 2);
  const authScore = Math.min(100, baseScore + (review?.security_sensitive_changes.length ?? 0) * 12);
  const dbScore = Math.min(100, baseScore + (review?.database_or_schema_changes.length ?? 0) * 10 + (review?.migration_warnings.length ?? 0) * 8);
  const scores = [apiScore, logicScore, authScore, dbScore];
  const center = 50;
  const maxRadius = 36;
  const angles = [-Math.PI / 2, 0, Math.PI / 2, Math.PI];
  return scores.map((score, idx) => {
    const radius = (Math.max(score, 8) / 100) * maxRadius;
    return {
      label: labels[idx],
      pct: Math.max(score, 8),
      level: score >= 75 ? "critical" : score >= 50 ? "high" : score >= 25 ? "medium" : "low",
      x: +(center + Math.cos(angles[idx]) * radius).toFixed(2),
      y: +(center + Math.sin(angles[idx]) * radius).toFixed(2)
    };
  });
}

function formatRelative(iso: string): string {
  const target = new Date(iso).getTime();
  if (Number.isNaN(target)) return iso;
  const diff = Date.now() - target;
  const minutes = Math.round(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function countBy(values: string[]): Record<string, number> {
  return values.reduce<Record<string, number>>((acc, value) => {
    acc[value] = (acc[value] ?? 0) + 1;
    return acc;
  }, {});
}

export type { Page };
