import type { GraphEdge, GraphNode, GraphPayload } from "@devgraph/schema";
import type { DerivedLayer, LayerId } from "../store/dashboardStore";

export const LAYER_DEFS: ReadonlyArray<{ id: LayerId; name: string; description: string; color: string }> = [
  { id: "entry", name: "Entry Points / API", description: "Endpoints, routers, CLIs, controllers.", color: "#FFB59D" },
  { id: "ui", name: "UI / Frontend", description: "Components, views, pages, client widgets.", color: "#D4BBFF" },
  { id: "app", name: "Application / Services", description: "Service objects, orchestrators, use-cases.", color: "#7CD7C4" },
  { id: "domain", name: "Domain / Business Logic", description: "Core entities, pure functions, models.", color: "#9EF9E5" },
  { id: "data", name: "Data / Persistence", description: "Tables, schemas, queries, migrations.", color: "#E8A55A" },
  { id: "infra", name: "Config / Infrastructure", description: "Config, terraform, k8s, CI, deploys.", color: "#FFD3B6" },
  { id: "tests", name: "Tests", description: "Test suites and fixtures.", color: "#5DB872" },
  { id: "docs", name: "Documentation", description: "Markdown, RST, knowledge.", color: "#D4BBFF" },
  { id: "memory", name: "Memory / Decisions", description: "Decisions, sessions, handoffs.", color: "#B388FF" },
];

const ENTRY_TYPES = new Set(["api_endpoint", "service", "pipeline", "resource", "schema"]);
const DATA_TYPES = new Set(["database_table", "schema"]);
const DOC_TYPES = new Set(["document", "section", "article", "claim", "entity"]);
const MEMORY_TYPES = new Set(["decision", "session"]);
const TEST_TYPES = new Set(["test"]);
const CONFIG_TYPES = new Set(["config"]);

const UI_PATH_RE = /(^|[\\/])(ui|components?|views?|pages?|frontend|web|client|webview)(?=[\\/]|$)/i;
const APP_PATH_RE = /(^|[\\/])(services?|app|orchestrat|use[-_]?case|workflow|handlers?|controllers?)(?=[\\/]|$)/i;
const ENTRY_PATH_RE = /(^|[\\/])(api|routes?|endpoints?|gateway|cli|server|http)(?=[\\/]|$)/i;
const DATA_PATH_RE = /(^|[\\/])(db|database|persistence|repository|repositories|models?|migrations?|sql|prisma)(?=[\\/]|$)/i;
const INFRA_PATH_RE = /(^|[\\/])(infra|terraform|k8s|kubernetes|helm|deploy|ops|\.github|ci)(?=[\\/]|$)/i;
const TEST_PATH_RE = /(^|[\\/])(tests?|__tests__|spec|specs|e2e)(?=[\\/]|$)/i;
const DOCS_PATH_RE = /(^|[\\/])(docs?|documentation|wiki)(?=[\\/]|$)|\.(md|mdx|rst|txt)$/i;
const CONFIG_PATH_RE = /\.(ya?ml|toml|ini|cfg|json5?|env)$|(^|[\\/])(config|configs|settings)(?=[\\/]|$)/i;
const DOMAIN_PATH_RE = /(^|[\\/])(domain|core|entities|business|logic|models?)(?=[\\/]|$)/i;

const FRAMEWORK_ROUTE_KEYS = new Set([
  "route",
  "routes",
  "framework",
  "framework_route",
  "route_kind",
  "is_route",
]);

/** Decide which layer a single node belongs to. First match wins. */
export function classifyNode(node: GraphNode): LayerId {
  // Type-based fast paths.
  if (TEST_TYPES.has(node.type)) return "tests";
  if (MEMORY_TYPES.has(node.type)) return "memory";
  if (DOC_TYPES.has(node.type)) return "docs";
  if (DATA_TYPES.has(node.type)) return "data";
  if (CONFIG_TYPES.has(node.type)) return "infra";

  // Framework route metadata → entry layer regardless of path.
  const metadata = node.metadata ?? {};
  for (const key of Object.keys(metadata)) {
    if (FRAMEWORK_ROUTE_KEYS.has(key) && metadata[key]) {
      return "entry";
    }
  }
  if (ENTRY_TYPES.has(node.type)) return "entry";

  const path = (node.file_path ?? "").replace(/\\/g, "/");

  if (path) {
    if (TEST_PATH_RE.test(path)) return "tests";
    if (DOCS_PATH_RE.test(path)) return "docs";
    if (CONFIG_PATH_RE.test(path)) return "infra";
    if (DATA_PATH_RE.test(path)) return "data";
    if (INFRA_PATH_RE.test(path)) return "infra";
    if (ENTRY_PATH_RE.test(path)) return "entry";
    if (UI_PATH_RE.test(path)) return "ui";
    if (APP_PATH_RE.test(path)) return "app";
    if (DOMAIN_PATH_RE.test(path)) return "domain";
  }

  // Language-based hint when path is ambiguous.
  if (node.language) {
    if (["tsx", "jsx", "vue", "svelte"].includes(node.language.toLowerCase())) return "ui";
    if (["sql"].includes(node.language.toLowerCase())) return "data";
  }

  // Fall back: classes/functions/modules without strong signal → app layer.
  if (["class", "function", "module", "type"].includes(node.type)) return "app";
  return "app";
}

export interface AdapterResult {
  layers: DerivedLayer[];
  nodeIdToLayerId: Map<string, LayerId>;
  edgesByNode: Map<string, GraphEdge[]>;
  inDegree: Map<string, number>;
  outDegree: Map<string, number>;
  topConnected: GraphNode[];
}

/**
 * Derive architecture layers from a DevGraph payload. Adds degree stats and
 * a top-connected hot-list for the Command Center to surface without re-
 * traversing the edge list.
 */
export function deriveArchitecture(graph: GraphPayload): AdapterResult {
  const nodeIdToLayerId = new Map<string, LayerId>();
  const layerBuckets = new Map<LayerId, GraphNode[]>();
  for (const def of LAYER_DEFS) layerBuckets.set(def.id, []);

  for (const node of graph.nodes) {
    const layerId = classifyNode(node);
    nodeIdToLayerId.set(node.id, layerId);
    layerBuckets.get(layerId)!.push(node);
  }

  const edgesByNode = new Map<string, GraphEdge[]>();
  const inDegree = new Map<string, number>();
  const outDegree = new Map<string, number>();
  for (const edge of graph.edges) {
    const fromList = edgesByNode.get(edge.source_id) ?? [];
    fromList.push(edge);
    edgesByNode.set(edge.source_id, fromList);
    const toList = edgesByNode.get(edge.target_id) ?? [];
    toList.push(edge);
    edgesByNode.set(edge.target_id, toList);
    outDegree.set(edge.source_id, (outDegree.get(edge.source_id) ?? 0) + 1);
    inDegree.set(edge.target_id, (inDegree.get(edge.target_id) ?? 0) + 1);
  }

  const layers: DerivedLayer[] = LAYER_DEFS.map((def) => {
    const nodes = layerBuckets.get(def.id) ?? [];
    const files = nodes.filter((node) => node.type === "file").length;
    const symbols = nodes.filter((node) => ["function", "class", "module", "type"].includes(node.type)).length;
    const tests = nodes.filter((node) => node.type === "test").length;
    const docs = nodes.filter((node) => DOC_TYPES.has(node.type)).length;
    return {
      id: def.id,
      name: def.name,
      description: def.description,
      color: def.color,
      nodeIds: nodes.map((node) => node.id),
      stats: { files, symbols, tests, docs },
    };
  }).filter((layer) => layer.nodeIds.length > 0);

  const topConnected = [...graph.nodes]
    .map((node) => ({ node, degree: (inDegree.get(node.id) ?? 0) + (outDegree.get(node.id) ?? 0) }))
    .filter((row) => row.degree > 0)
    .sort((a, b) => b.degree - a.degree)
    .slice(0, 12)
    .map((row) => row.node);

  return { layers, nodeIdToLayerId, edgesByNode, inDegree, outDegree, topConnected };
}

/** Map review.changed_nodes / impacted_nodes onto layer ids for the diff overlay. */
export function mapReviewToLayers(
  changedIds: string[],
  affectedIds: string[],
  nodeIdToLayerId: Map<string, LayerId>
): { changedByLayer: Map<LayerId, number>; affectedByLayer: Map<LayerId, number> } {
  const changedByLayer = new Map<LayerId, number>();
  const affectedByLayer = new Map<LayerId, number>();
  for (const id of changedIds) {
    const layerId = nodeIdToLayerId.get(id);
    if (!layerId) continue;
    changedByLayer.set(layerId, (changedByLayer.get(layerId) ?? 0) + 1);
  }
  for (const id of affectedIds) {
    const layerId = nodeIdToLayerId.get(id);
    if (!layerId) continue;
    affectedByLayer.set(layerId, (affectedByLayer.get(layerId) ?? 0) + 1);
  }
  return { changedByLayer, affectedByLayer };
}
