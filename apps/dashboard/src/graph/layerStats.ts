import type { GraphNode } from "@devgraph/schema";
import type { DerivedLayer } from "../store/dashboardStore";

export interface LayerStatsRich {
  layerId: string;
  resolvedCount: number;
  changedCount: number;
  affectedCount: number;
  searchMatchCount: number;
  riskLevel: "low" | "medium" | "high";
  complexitySummary: "simple" | "moderate" | "complex";
}

/**
 * O(layer.nodeIds.length) summary per layer. Risk uses ambiguous-confidence
 * count as a proxy until we wire ReviewEngine severity_by_symbol into the
 * dashboard.
 */
export function computeLayerStats(
  layer: DerivedLayer,
  nodesById: Map<string, GraphNode>,
  options: {
    changedIds?: Set<string>;
    affectedIds?: Set<string>;
    searchMatchIds?: Set<string>;
  } = {},
): LayerStatsRich {
  let resolved = 0;
  let changed = 0;
  let affected = 0;
  let matches = 0;
  let ambiguous = 0;
  for (const nid of layer.nodeIds) {
    const node = nodesById.get(nid);
    if (!node) continue;
    resolved++;
    if (options.changedIds?.has(nid)) changed++;
    if (options.affectedIds?.has(nid)) affected++;
    if (options.searchMatchIds?.has(nid)) matches++;
    if (node.confidence_tier === "ambiguous" || node.confidence_tier === "inferred") {
      ambiguous++;
    }
  }
  const ambiguousRatio = resolved === 0 ? 0 : ambiguous / resolved;
  const complexitySummary: LayerStatsRich["complexitySummary"] =
    resolved > 80 ? "complex" : resolved > 30 ? "moderate" : "simple";
  const riskLevel: LayerStatsRich["riskLevel"] =
    changed > 0 || ambiguousRatio > 0.4
      ? "high"
      : affected > 0 || ambiguousRatio > 0.2
        ? "medium"
        : "low";
  return {
    layerId: layer.id,
    resolvedCount: resolved,
    changedCount: changed,
    affectedCount: affected,
    searchMatchCount: matches,
    riskLevel,
    complexitySummary,
  };
}
