import { useCallback } from "react";
import { ReactFlow, Background, Controls, MiniMap, type NodeMouseHandler } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useViewStore } from "../../store/viewStore";
import { useWorkspace } from "../../hooks/useWorkspace";
import { SystemNode } from "./nodes/SystemNode";
import { ContainerNode } from "./nodes/ContainerNode";
import { ComponentNode } from "./nodes/ComponentNode";
import { PersonNode } from "./nodes/PersonNode";
import { ExternalNode } from "./nodes/ExternalNode";
import { RelationEdge } from "./edges/RelationEdge";
import { Breadcrumb } from "../Breadcrumb";

const nodeTypes = {
  system: SystemNode,
  container: ContainerNode,
  component: ComponentNode,
  person: PersonNode,
  external: ExternalNode,
};

const edgeTypes = {
  relation: RelationEdge,
};

export function C4Graph() {
  const viewState = useViewStore();
  const { drillToC2, drillToC3, level } = viewState;
  const { nodes, edges, isLoading } = useWorkspace(viewState);

  const onNodeDoubleClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      if (level === "C1" && node.type === "system") {
        drillToC2(node.id);
      } else if (level === "C2" && node.type === "container") {
        drillToC3(node.id);
      }
    },
    [level, drillToC2, drillToC3],
  );

  if (isLoading) {
    return <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>Loading...</div>;
  }

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <Breadcrumb />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodeDoubleClick={onNodeDoubleClick}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
