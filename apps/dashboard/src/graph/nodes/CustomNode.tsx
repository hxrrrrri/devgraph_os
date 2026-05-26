import { memo } from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import clsx from "clsx";
import type { GraphNode } from "@devgraph/schema";

export interface CustomNodeData extends Record<string, unknown> {
  node: GraphNode;
  isSelected: boolean;
  isSearchHighlighted: boolean;
  searchScore?: number;
  isDiffChanged: boolean;
  isDiffAffected: boolean;
  isDiffFaded: boolean;
  isNeighbor: boolean;
  isSelectionFaded: boolean;
  isTourHighlighted: boolean;
  isRisky: boolean;
  isAmbiguous: boolean;
  isOnPath: boolean;
  hasTests: boolean;
  hasDocs: boolean;
  onSelect?: (id: string) => void;
}

export type CustomFlowNode = Node<CustomNodeData, "dg-custom">;

const TYPE_COLOR: Record<string, string> = {
  file: "var(--primary-coral-bright)",
  module: "var(--accent-teal)",
  function: "var(--knowledge-violet)",
  class: "var(--knowledge-violet)",
  type: "var(--knowledge-violet)",
  test: "var(--success)",
  api_endpoint: "var(--primary-coral-bright)",
  service: "var(--accent-teal)",
  pipeline: "var(--accent-amber)",
  database_table: "var(--accent-amber)",
  schema: "var(--accent-amber)",
  config: "var(--accent-amber)",
  document: "var(--knowledge-violet)",
  section: "var(--knowledge-violet)",
  article: "var(--knowledge-violet)",
  claim: "var(--knowledge-violet)",
  entity: "var(--knowledge-violet)",
  resource: "var(--accent-teal)",
  decision: "var(--knowledge-violet)",
  session: "var(--knowledge-violet)",
  commit: "var(--muted-dark)",
  pull_request: "var(--muted-dark)",
  domain: "var(--accent-teal)",
  flow: "var(--accent-amber)",
  step: "var(--knowledge-violet)",
  repository: "var(--primary-coral-bright)",
};

function CustomNodeImpl({ id, data }: NodeProps<CustomFlowNode>) {
  const { node } = data;
  const barColor = TYPE_COLOR[node.type] ?? "var(--muted-dark)";
  const label = node.name.length > 28 ? `${node.name.slice(0, 26)}…` : node.name;
  const path = node.file_path ? node.file_path.split(/[\\/]/).slice(-2).join("/") : "external";

  return (
    <div
      className={clsx(
        "dg-node",
        data.isSelected && "is-selected",
        data.isSearchHighlighted && "is-search-hit",
        data.isDiffChanged && "is-diff-changed",
        data.isDiffAffected && "is-diff-affected",
        data.isDiffFaded && "is-diff-faded",
        data.isSelectionFaded && "is-selection-faded",
        data.isNeighbor && "is-neighbor",
        data.isTourHighlighted && "is-tour-highlighted",
        data.isRisky && "is-risky",
        data.isAmbiguous && "is-ambiguous",
        data.isOnPath && "is-on-path",
      )}
      onClick={() => data.onSelect?.(id)}
    >
      <span className="dg-node-bar" style={{ background: barColor }} />
      <Handle type="target" position={Position.Top} className="dg-handle" />
      <div className="dg-node-body">
        <div className="dg-node-head">
          <span className="dg-node-type" style={{ color: barColor }}>{node.type}</span>
          <span className="dg-node-tier">{node.confidence_tier}</span>
        </div>
        <div className="dg-node-title" title={node.qualified_name}>{label}</div>
        <div className="dg-node-meta">{path}</div>
        <div className="dg-node-flags">
          {data.hasTests ? <span className="dg-flag flag-test" title="Has tests">T</span> : null}
          {data.hasDocs ? <span className="dg-flag flag-doc" title="Has docs">D</span> : null}
          {data.isRisky ? <span className="dg-flag flag-risk" title="Risky / changed">!</span> : null}
          {data.isAmbiguous ? <span className="dg-flag flag-amb" title="Ambiguous fact">?</span> : null}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="dg-handle" />
    </div>
  );
}

export const CustomNode = memo(CustomNodeImpl);
CustomNode.displayName = "CustomNode";
