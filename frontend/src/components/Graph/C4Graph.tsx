import { useCallback, useEffect, useRef } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type NodeMouseHandler,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useViewStore, buildViewKey } from "../../store/viewStore";
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
  const { drillToC2, drillToC3, level, systemId, containerId, layoutCache, saveLayout } = viewState;
  const { nodes: fetchedNodes, edges: fetchedEdges, isLoading } = useWorkspace(viewState);

  const viewKey = buildViewKey(level, systemId, containerId);

  const [nodes, setNodes, onNodesChange] = useNodesState(fetchedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(fetchedEdges);

  // Ref so the fetchedNodes effect reads latest cache without re-running on every drag save.
  const layoutCacheRef = useRef(layoutCache);
  useEffect(() => { layoutCacheRef.current = layoutCache; }, [layoutCache]);

  useEffect(() => {
    const saved = layoutCacheRef.current[viewKey];
    if (saved && fetchedNodes.length > 0) {
      setNodes(fetchedNodes.map((n) => saved[n.id] ? { ...n, position: saved[n.id] } : n));
    } else {
      setNodes(fetchedNodes);
    }
  }, [fetchedNodes, viewKey, setNodes]);

  useEffect(() => {
    setEdges(fetchedEdges);
  }, [fetchedEdges, setEdges]);

  const onNodeDragStop = useCallback(
    (_event: unknown, _node: Node, allNodes: Node[]) => {
      const positions: Record<string, { x: number; y: number }> = {};
      for (const n of allNodes) positions[n.id] = n.position;
      saveLayout(viewKey, positions);
    },
    [viewKey, saveLayout],
  );

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
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeDragStop={onNodeDragStop}
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
