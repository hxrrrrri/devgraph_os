import { memo } from "react";
import type { Node, NodeProps } from "@xyflow/react";
import clsx from "clsx";

export interface ContainerNodeData extends Record<string, unknown> {
  containerId: string;
  name: string;
  childCount: number;
  strategy: "folder" | "community";
  isExpanded: boolean;
  hasSearchHits: boolean;
  searchHitCount?: number;
  isDiffAffected: boolean;
  isFocusedViaChild: boolean;
  onToggle: (id: string) => void;
}

export type ContainerFlowNode = Node<ContainerNodeData, "dg-container">;

function ContainerImpl({ data, width, height }: NodeProps<ContainerFlowNode>) {
  const labelDimmed = data.name === "~";
  const labelText = labelDimmed ? "(root)" : data.name;
  const handleToggle = (e: React.SyntheticEvent) => {
    e.stopPropagation();
    data.onToggle(data.containerId);
  };
  return (
    <div
      role="button"
      tabIndex={0}
      aria-expanded={data.isExpanded}
      aria-label={`${labelText} container, ${data.childCount} items, ${data.isExpanded ? "expanded" : "collapsed"}`}
      className={clsx(
        "dg-container",
        data.isExpanded && "is-expanded",
        data.isFocusedViaChild && "is-focused",
        data.isDiffAffected && "is-diff-affected",
      )}
      style={{ width, height }}
      onClick={handleToggle}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleToggle(e);
        }
      }}
    >
      <div className="dg-container-head">
        <span className={clsx("dg-container-name", labelDimmed && "is-dim")}>
          {data.isExpanded ? "▾ " : "▸ "}
          {labelText}
          {data.searchHitCount ? (
            <span className="dg-badge badge-match" style={{ marginLeft: 6 }}>{data.searchHitCount} hit</span>
          ) : null}
        </span>
        <span className="dg-container-count">{data.childCount}</span>
      </div>
    </div>
  );
}

export const ContainerNode = memo(ContainerImpl);
ContainerNode.displayName = "ContainerNode";
