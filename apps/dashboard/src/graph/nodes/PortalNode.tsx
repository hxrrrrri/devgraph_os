import { memo } from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";

export interface PortalNodeData extends Record<string, unknown> {
  targetLayerId: string;
  targetLayerName: string;
  connectionCount: number;
  color: string;
  onTravel: (layerId: string) => void;
}

export type PortalFlowNode = Node<PortalNodeData, "dg-portal">;

function PortalImpl({ data }: NodeProps<PortalFlowNode>) {
  return (
    <div
      className="dg-portal"
      onClick={() => data.onTravel(data.targetLayerId)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          data.onTravel(data.targetLayerId);
        }
      }}
      style={{ borderColor: data.color }}
    >
      <Handle type="target" position={Position.Top} className="dg-handle" />
      <span className="dg-portal-eyebrow" style={{ color: data.color }}>portal</span>
      <span className="dg-portal-name">{data.targetLayerName}</span>
      <span className="dg-portal-meta">{data.connectionCount} edge{data.connectionCount === 1 ? "" : "s"}</span>
      <Handle type="source" position={Position.Bottom} className="dg-handle" />
    </div>
  );
}

export const PortalNode = memo(PortalImpl);
PortalNode.displayName = "PortalNode";
