import { RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { GraphPayload, GraphStatus, ReviewResult } from "@devgraph/schema";
import { client } from "./api/client";
import { DebugLens } from "./debug/DebugLens";
import { GraphView } from "./graph/GraphView";
import { KnowledgeLens } from "./knowledge/KnowledgeLens";
import { OnboardingLens } from "./onboard/OnboardingLens";
import { ReviewLens } from "./review/ReviewLens";

type Page = "overview" | "graph" | "review" | "debug" | "onboard" | "knowledge";

export function App() {
  const [page, setPage] = useState<Page>("overview");
  const [status, setStatus] = useState<GraphStatus | null>(null);
  const [graph, setGraph] = useState<GraphPayload>({ nodes: [], edges: [] });
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setError(null);
      const [nextStatus, nextGraph] = await Promise.all([client.status(), client.graph()]);
      setStatus(nextStatus);
      setGraph(nextGraph);
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

  const filteredGraph = useMemo(() => {
    if (!search.trim()) return graph;
    const term = search.toLowerCase();
    const nodes = graph.nodes.filter((node) => node.qualified_name.toLowerCase().includes(term));
    const ids = new Set(nodes.map((node) => node.id));
    return {
      nodes,
      edges: graph.edges.filter((edge) => ids.has(edge.source_id) && ids.has(edge.target_id))
    };
  }, [graph, search]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">DevGraph OS</div>
        {(["overview", "graph", "review", "debug", "onboard", "knowledge"] as Page[]).map((item) => (
          <button key={item} className={page === item ? "nav-item active" : "nav-item"} onClick={() => setPage(item)}>
            {item}
          </button>
        ))}
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{status?.project ?? "DevGraph Project"}</h1>
            <p>{status?.last_indexed_at ? `Last indexed ${status.last_indexed_at}` : "Graph has not been indexed yet"}</p>
          </div>
          <div className="toolbar">
            <label className="search">
              <Search size={16} />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search graph" />
            </label>
            <button className="icon-button" onClick={() => void refresh()} title="Refresh">
              <RefreshCw size={18} />
            </button>
          </div>
        </header>

        {error ? <div className="alert">{error}</div> : null}

        {page === "overview" ? <Overview status={status} graph={graph} /> : null}
        {page === "graph" ? <GraphView graph={filteredGraph} /> : null}
        {page === "review" ? <ReviewLens review={review} onLoadReview={() => void loadReview()} /> : null}
        {page === "debug" ? <DebugLens graph={filteredGraph} /> : null}
        {page === "onboard" ? <OnboardingLens status={status} /> : null}
        {page === "knowledge" ? <KnowledgeLens graph={filteredGraph} /> : null}
      </main>
    </div>
  );
}

function Overview({ status, graph }: { status: GraphStatus | null; graph: GraphPayload }) {
  const languageRows = Object.entries(status?.languages ?? {});
  const riskyNodes = graph.nodes.filter((node) => node.type === "api_endpoint" || node.type === "schema").slice(0, 8);
  return (
    <section className="overview-grid">
      <Metric label="Files" value={status?.total_files ?? 0} />
      <Metric label="Nodes" value={status?.total_nodes ?? 0} />
      <Metric label="Edges" value={status?.total_edges ?? 0} />
      <Metric label="Chunks" value={status?.total_chunks ?? 0} />
      <section className="panel wide">
        <h2>Languages</h2>
        <div className="list">
          {languageRows.length ? languageRows.map(([language, count]) => <span key={language}>{language}: {count}</span>) : <span>No language data</span>}
        </div>
      </section>
      <section className="panel wide">
        <h2>Risk hotspots</h2>
        <div className="list">
          {riskyNodes.length ? riskyNodes.map((node) => <span key={node.id}>{node.qualified_name}</span>) : <span>No hotspot signals yet</span>}
        </div>
      </section>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <section className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </section>
  );
}

