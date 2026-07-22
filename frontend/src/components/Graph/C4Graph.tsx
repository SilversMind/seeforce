/*
@c3:component
name: Architecture visualiser
container: Frontend
technology: ReactFlow
description: Display architecture and manage user interaction such as drilling down on specific component
uses:
- Node manager
*/
import { useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useViewStore } from "../../store/viewStore";
import { useWorkspace } from "../../hooks/useWorkspace";
import { applyElkLayout } from "../../lib/elkLayout";
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
  const {
    nodes: fetchedNodes,
    edges: fetchedEdges,
    isLoading,
  } = useWorkspace(viewState);

  const [nodes, setNodes, onNodesChange] = useNodesState(fetchedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(fetchedEdges);
  const [isLayouting, setIsLayouting] = useState(false);

  useEffect(() => {
    if (fetchedNodes.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }
    setIsLayouting(true);
    applyElkLayout(fetchedNodes, fetchedEdges)
      .then((laidOut) => {
        setNodes(laidOut);
        setEdges(fetchedEdges);
      })
      .finally(() => setIsLayouting(false));
  }, [fetchedNodes, fetchedEdges, setNodes, setEdges]);

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

  if (isLoading || isLayouting) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
        }}
      >
        {isLayouting ? "Computing layout…" : "Loading…"}
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <Breadcrumb />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
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
