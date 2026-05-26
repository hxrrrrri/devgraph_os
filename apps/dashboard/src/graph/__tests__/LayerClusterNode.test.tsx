import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ReactFlowProvider } from "@xyflow/react";
import { LayerClusterNode, type LayerClusterFlowNode } from "../nodes/LayerClusterNode";
import type { NodeProps } from "@xyflow/react";

function renderNode(overrides: Partial<LayerClusterFlowNode["data"]> = {}) {
  const onDrillIn = vi.fn();
  const data: LayerClusterFlowNode["data"] = {
    layerId: "app",
    name: "Application / Services",
    description: "Service objects, orchestrators, use-cases.",
    color: "#7CD7C4",
    fileCount: 4,
    symbolCount: 12,
    testCount: 3,
    docCount: 1,
    changedCount: 0,
    affectedCount: 0,
    searchMatchCount: 0,
    riskLevel: "low",
    onDrillIn,
    ...overrides,
  };
  const props = {
    id: "app",
    data,
    type: "dg-layer-cluster",
    dragHandle: undefined,
    selected: false,
    dragging: false,
    isConnectable: false,
    zIndex: 0,
    positionAbsoluteX: 0,
    positionAbsoluteY: 0,
    selectable: false,
    deletable: false,
    draggable: false,
    width: 300,
    height: 170,
  } as unknown as NodeProps<LayerClusterFlowNode>;
  render(
    <ReactFlowProvider>
      <LayerClusterNode {...props} />
    </ReactFlowProvider>,
  );
  return { onDrillIn };
}

describe("LayerClusterNode", () => {
  it("renders the layer name, description, and stat counts", () => {
    renderNode();
    expect(screen.getByText("Application / Services")).toBeInTheDocument();
    expect(screen.getByText("Service objects, orchestrators, use-cases.")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("calls onDrillIn when the cluster is clicked", () => {
    const { onDrillIn } = renderNode();
    fireEvent.click(screen.getByText("Application / Services"));
    expect(onDrillIn).toHaveBeenCalledWith("app");
  });

  it("surfaces changed and affected badges when counts are non-zero", () => {
    renderNode({ changedCount: 2, affectedCount: 5, riskLevel: "high" });
    expect(screen.getByText(/2 changed/)).toBeInTheDocument();
    expect(screen.getByText(/5 affected/)).toBeInTheDocument();
    expect(screen.getByText(/high risk/)).toBeInTheDocument();
  });
});
