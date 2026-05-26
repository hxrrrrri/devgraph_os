import { memo } from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import clsx from "clsx";

export interface LayerClusterData extends Record<string, unknown> {
  layerId: string;
  name: string;
  description: string;
  color: string;
  fileCount: number;
  symbolCount: number;
  testCount: number;
  docCount: number;
  changedCount: number;
  affectedCount: number;
  searchMatchCount: number;
  riskLevel: "low" | "medium" | "high";
  onDrillIn: (layerId: string) => void;
}

export type LayerClusterFlowNode = Node<LayerClusterData, "dg-layer-cluster">;

function LayerClusterImpl({ data }: NodeProps<LayerClusterFlowNode>) {
  return (
    <div
      className={clsx("dg-layer-cluster", `risk-${data.riskLevel}`)}
      onClick={() => data.onDrillIn(data.layerId)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          data.onDrillIn(data.layerId);
        }
      }}
    >
      <span className="dg-layer-bar" style={{ background: data.color }} />
      <Handle type="target" position={Position.Top} className="dg-handle" />
      <div className="dg-layer-body">
        <div className="dg-layer-head">
          <span className="dg-layer-tag" style={{ color: data.color }}>layer</span>
          <div className="dg-layer-badges">
            {data.changedCount > 0 ? (
              <span className="dg-badge badge-changed">{data.changedCount} changed</span>
            ) : null}
            {data.affectedCount > 0 ? (
              <span className="dg-badge badge-affected">{data.affectedCount} affected</span>
            ) : null}
            {data.searchMatchCount > 0 ? (
              <span className="dg-badge badge-match">{data.searchMatchCount} match</span>
            ) : null}
          </div>
        </div>
        <div className="dg-layer-title">{data.name}</div>
        <div className="dg-layer-desc">{data.description}</div>
        <div className="dg-layer-stats">
          <span><b>{data.fileCount}</b> files</span>
          <span><b>{data.symbolCount}</b> symbols</span>
          <span><b>{data.testCount}</b> tests</span>
          <span><b>{data.docCount}</b> docs</span>
        </div>
        <div className="dg-layer-foot">
          <span className={`dg-risk-pill risk-${data.riskLevel}`}>{data.riskLevel} risk</span>
          <span className="dg-layer-cta">drill in →</span>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="dg-handle" />
    </div>
  );
}

export const LayerClusterNode = memo(LayerClusterImpl);
LayerClusterNode.displayName = "LayerClusterNode";
