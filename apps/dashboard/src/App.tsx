import {
  Activity,
  BookOpen,
  Brain,
  Bug,
  Command,
  GitBranch,
  GitPullRequest,
  LayoutDashboard,
  Network,
  Radar,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Waypoints,
  type LucideIcon
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import clsx from "clsx";
import type { GraphPayload, GraphStatus, ReviewResult } from "@devgraph/schema";
import { client } from "./api/client";
import { DebugLens } from "./debug/DebugLens";
import { GraphView } from "./graph/GraphView";
import { KnowledgeLens } from "./knowledge/KnowledgeLens";
import { OnboardingLens } from "./onboard/OnboardingLens";
import { ReviewLens } from "./review/ReviewLens";

type Page = "overview" | "graph" | "review" | "debug" | "onboard" | "knowledge" | "flows";
type Memory = { id: string; kind: string; content: string; created_at?: string };

const navItems: Array<{ id: Page; label: string; icon: LucideIcon }> = [
  { id: "overview", label: "Command", icon: LayoutDashboard },
  { id: "graph", label: "Graph", icon: Network },
  { id: "review", label: "Review", icon: GitPullRequest },
  { id: "debug", label: "Debug", icon: Bug },
  { id: "onboard", label: "Onboard", icon: BookOpen },
  { id: "knowledge", label: "Knowledge", icon: Brain },
  { id: "flows", label: "Flows", icon: Waypoints }
];

const nodeColors: Record<string, string> = {
  file: "#38bdf8",
  module: "#2dd4bf",
  function: "#a3e635",
  class: "#c084fc",
  test: "#facc15",
  api_endpoint: "#fb7185",
  config: "#f59e0b",
  document: "#93c5fd",
  section: "#60a5fa",
  database_table: "#fb923c",
  resource: "#34d399"
};

export function App() {
  const [page, setPage] = useState<Page>("overview");
  const [status, setStatus] = useState<GraphStatus | null>(null);
  const [graph, setGraph] = useState<GraphPayload>({ nodes: [], edges: [] });
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [search, setSearch] = useState("");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setError(null);
      const [nextStatus, nextGraph, nextReview, memoryPayload] = await Promise.allSettled([
        client.status(),
        client.graph(),
        client.review(),
        client.memories()
      ]);
      if (nextStatus.status === "fulfilled") setStatus(nextStatus.value);
      if (nextGraph.status === "fulfilled") setGraph(nextGraph.value);
      if (nextReview.status === "fulfilled") setReview(nextReview.value);
      if (memoryPayload.status === "fulfilled") {
        const payload = memoryPayload.value as { memories?: Memory[] };
        setMemories(payload.memories ?? []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load DevGraph data");
    }
  }

  async function loadReview() {
    try {
      const nextReview = await client.review();
      setReview(nextReview);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load review data");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((value) => !value);
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);

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

  const currentPage = navItems.find((item) => item.id === page);
  const CurrentIcon = currentPage?.icon;

  return (
    <div className="app-shell">
      <aside className="rail" aria-label="DevGraph navigation">
        <div className="rail-logo"><Activity size={21} /></div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={clsx("rail-button", page === item.id && "active")}
              onClick={() => setPage(item.id)}
              title={item.label}
            >
              <Icon size={19} />
            </button>
          );
        })}
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="project-mark">
            <span className="eyebrow"><Sparkles size={14} /> DevGraph OS</span>
            <h1>{status?.project ?? "Local Graph"}</h1>
          </div>
          <div className="command-bar">
            <label className="search">
              <Search size={17} />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search graph, symbols, files" />
            </label>
            <StatusPill icon={GitBranch} label="Branch" value="local" />
            <StatusPill icon={ShieldCheck} label="Freshness" value={status?.last_indexed_at ? "indexed" : "stale"} />
            <button className="icon-button" onClick={() => void refresh()} title="Refresh">
              <RefreshCw size={18} />
            </button>
            <button className="icon-button" onClick={() => setPaletteOpen(true)} title="Command palette">
              <Command size={18} />
            </button>
          </div>
        </header>

        {error ? <div className="alert">{error}</div> : null}

        <AnimatePresence mode="wait">
          <motion.section
            key={page}
            className="page-frame"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
          >
            <div className="page-title">
              {CurrentIcon ? <CurrentIcon size={20} /> : null}
              <span>{currentPage?.label}</span>
            </div>
            {page === "overview" ? <Overview status={status} graph={graph} review={review} memories={memories} onReview={() => void loadReview()} /> : null}
            {page === "graph" ? <GraphView graph={filteredGraph} /> : null}
            {page === "review" ? <ReviewLens review={review} onLoadReview={() => void loadReview()} /> : null}
            {page === "debug" ? <DebugLens graph={filteredGraph} /> : null}
            {page === "onboard" ? <OnboardingLens status={status} graph={graph} /> : null}
            {page === "knowledge" ? <KnowledgeLens graph={filteredGraph} /> : null}
            {page === "flows" ? <FlowLens graph={filteredGraph} /> : null}
          </motion.section>
        </AnimatePresence>
      </main>

      {paletteOpen ? (
        <div className="palette-backdrop" onClick={() => setPaletteOpen(false)}>
          <div className="palette" onClick={(event) => event.stopPropagation()}>
            <div className="palette-head"><Command size={18} /> Commands</div>
            {navItems.map((item) => (
              <button key={item.id} onClick={() => { setPage(item.id); setPaletteOpen(false); }}>
                <item.icon size={16} />
                <span>{item.label}</span>
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
  onReview
}: {
  status: GraphStatus | null;
  graph: GraphPayload;
  review: ReviewResult | null;
  memories: Memory[];
  onReview: () => void;
}) {
  const languageRows = Object.entries(status?.languages ?? {}).map(([name, value]) => ({ name, value }));
  const typeRows = Object.entries(countBy(graph.nodes.map((node) => node.type))).map(([name, value]) => ({ name, value }));
  const confidenceRows = Object.entries(countBy(graph.nodes.map((node) => node.confidence_tier))).map(([name, value]) => ({ name, value }));
  const hotspots = graph.nodes
    .filter((node) => ["api_endpoint", "schema", "database_table", "config"].includes(node.type) || /auth|token|secret|payment/i.test(node.qualified_name))
    .slice(0, 8);

  return (
    <section className="command-grid">
      <Metric icon={BookOpen} label="Files" value={status?.total_files ?? 0} tone="cyan" />
      <Metric icon={Network} label="Nodes" value={status?.total_nodes ?? 0} tone="teal" />
      <Metric icon={Waypoints} label="Edges" value={status?.total_edges ?? 0} tone="green" />
      <Metric icon={GitPullRequest} label="Risk" value={review?.risk_score ?? 0} suffix="/100" tone={review?.risk_level === "high" || review?.risk_level === "critical" ? "orange" : "teal"} />

      <section className="glass-card hero-card">
        <div>
          <span className="eyebrow"><Radar size={14} /> Graph Pulse</span>
          <h2>{review?.risk_level ? `${review.risk_level} review posture` : "Graph intelligence online"}</h2>
          <p>{status?.last_indexed_at ? `Last indexed ${status.last_indexed_at}` : "Build the graph to unlock freshness signals."}</p>
          <div className="action-row">
            <button className="primary" onClick={onReview}>Run review</button>
            <button className="ghost" onClick={() => navigator.clipboard?.writeText(review?.context_pack ?? "")}>Copy context</button>
          </div>
        </div>
        <div className="graph-orbit" aria-hidden="true">
          <i /><i /><i /><i />
        </div>
      </section>

      <ChartCard title="Languages">
        <ResponsiveContainer width="100%" height={210}>
          <BarChart data={languageRows}>
            <XAxis dataKey="name" stroke="#7f8ea3" tick={{ fill: "#9fb0c8", fontSize: 11 }} />
            <YAxis stroke="#7f8ea3" tick={{ fill: "#9fb0c8", fontSize: 11 }} allowDecimals={false} />
            <Tooltip contentStyle={{ background: "#111822", border: "1px solid #243244", color: "#dce7f7" }} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]} fill="#2dd4bf" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Node Types">
        <ResponsiveContainer width="100%" height={210}>
          <PieChart>
            <Pie data={typeRows.slice(0, 8)} dataKey="value" nameKey="name" innerRadius={46} outerRadius={82} paddingAngle={3}>
              {typeRows.slice(0, 8).map((row) => <Cell key={row.name} fill={nodeColors[row.name] ?? "#64748b"} />)}
            </Pie>
            <Tooltip contentStyle={{ background: "#111822", border: "1px solid #243244", color: "#dce7f7" }} />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>

      <section className="glass-card">
        <h3>Confidence</h3>
        <div className="confidence-stack">
          {confidenceRows.map((row) => (
            <div key={row.name}>
              <span>{row.name}</span>
              <strong>{row.value}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="glass-card">
        <h3>Risk Hotspots</h3>
        <div className="dense-list">
          {hotspots.length ? hotspots.map((node) => (
            <span key={node.id}><b>{node.type}</b>{node.qualified_name}</span>
          )) : <em>No hotspot signals yet.</em>}
        </div>
      </section>

      <section className="glass-card wide-card">
        <h3>Memories / Sessions</h3>
        <div className="timeline">
          {memories.length ? memories.slice(0, 6).map((memory) => (
            <div key={memory.id}>
              <i />
              <span>{memory.kind}</span>
              <p>{memory.content}</p>
            </div>
          )) : <em>No memories recorded.</em>}
        </div>
      </section>

      <section className="glass-card wide-card">
        <h3>System Health</h3>
        <div className="health-strip">
          <Health label="Graph" ok={(status?.total_nodes ?? 0) > 0} />
          <Health label="Chunks" ok={(status?.total_chunks ?? 0) > 0} />
          <Health label="Review" ok={Boolean(review)} />
          <Health label="Warnings" ok={(status?.warnings.length ?? 0) === 0} />
        </div>
      </section>
    </section>
  );
}

function FlowLens({ graph }: { graph: GraphPayload }) {
  const flowEdges = graph.edges.filter((edge) => ["calls", "routes_to", "reads_from", "writes_to", "depends_on"].includes(edge.type)).slice(0, 24);
  const byId = new Map(graph.nodes.map((node) => [node.id, node]));
  return (
    <section className="lens flow-lens">
      <section className="glass-card hero-card">
        <div>
          <span className="eyebrow"><Waypoints size={14} /> Execution and data paths</span>
          <h2>{flowEdges.length} graph flow edges in view</h2>
          <p>Calls, routes, database references, and dependencies are shown from the current graph filter.</p>
        </div>
        <div className="flow-pulse" aria-hidden="true" />
      </section>
      <section className="glass-card">
        <h3>Flow Chains</h3>
        <div className="flow-list">
          {flowEdges.length ? flowEdges.map((edge) => (
            <div key={edge.id}>
              <span>{byId.get(edge.source_id)?.qualified_name ?? edge.source_id}</span>
              <b>{edge.type}</b>
              <span>{byId.get(edge.target_id)?.qualified_name ?? edge.target_id}</span>
            </div>
          )) : <em>No flow edges in the current graph view.</em>}
        </div>
      </section>
    </section>
  );
}

function Metric({ icon: Icon, label, value, suffix = "", tone }: { icon: LucideIcon; label: string; value: number; suffix?: string; tone: string }) {
  return (
    <motion.section className={clsx("metric", tone)} whileHover={{ y: -3 }} transition={{ duration: 0.15 }}>
      <Icon size={18} />
      <span>{label}</span>
      <strong>{value}{suffix}</strong>
    </motion.section>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="glass-card chart-card">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function StatusPill({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <span className="status-pill"><Icon size={14} /><b>{label}</b>{value}</span>
  );
}

function Health({ label, ok }: { label: string; ok: boolean }) {
  return <span className={clsx("health", ok ? "ok" : "warn")}>{label}</span>;
}

function countBy(values: string[]): Record<string, number> {
  return values.reduce<Record<string, number>>((acc, value) => {
    acc[value] = (acc[value] ?? 0) + 1;
    return acc;
  }, {});
}
