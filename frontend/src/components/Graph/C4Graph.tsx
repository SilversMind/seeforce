/*
@c3:component
name: Architecture Visualizer
container: Frontend
technology: ReactFlow
description: Display architecture and manage user interaction such as drilling down on specific component
uses:
- Node manager: "Renders C4 element nodes in the ReactFlow canvas"
- Edge manager: "Renders directional relationship edges between nodes"
*/
import { useCallback, useEffect, useRef, useState } from "react";
import useSWR, { mutate } from "swr";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  ConnectionMode,
  useNodesState,
  useEdgesState,
  type NodeMouseHandler,
  type EdgeMouseHandler,
  type OnNodeDrag,
  type ReactFlowInstance,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useViewStore } from "../../store/viewStore";
import { useWorkspace } from "../../hooks/useWorkspace";
import { applyElkLayout } from "../../lib/elkLayout";
import { loadPositions, savePositions } from "../../lib/layoutStorage";
import { type RFNode, type RFEdge, fetchLexicon } from "../../services/api";
import { GraphModeContext, type GraphMode } from "../../contexts/GraphModeContext";
import { LexiconContext } from "../../contexts/LexiconContext";
import type { LexiconEntry } from "../../lib/lexicon";
import { SystemNode } from "./nodes/SystemNode";
import { ContainerNode } from "./nodes/ContainerNode";
import { ComponentNode } from "./nodes/ComponentNode";
import { PersonNode } from "./nodes/PersonNode";
import { ExternalNode } from "./nodes/ExternalNode";
import { FloatingEdge } from "./edges/FloatingEdge";
import { Breadcrumb } from "../Breadcrumb";
import { OverlaySidebar } from "./OverlaySidebar";
import { LexiconBottomPanel } from "./LexiconBottomPanel";

const nodeTypes = {
  system: SystemNode,
  container: ContainerNode,
  component: ComponentNode,
  person: PersonNode,
  external: ExternalNode,
};

const edgeTypes = {
  relation: FloatingEdge,
};

type SidebarTarget =
  | { kind: "node"; node: RFNode }
  | { kind: "edge"; edge: RFEdge };

export function C4Graph() {
  const viewState = useViewStore();
  const {
    drillToC2,
    drillToC3,
    level,
    projectMapId: rawProjectMapId,
    systemId,
    containerId,
  } = viewState;
  const projectMapId = rawProjectMapId != null ? String(rawProjectMapId) : null;
  const {
    nodes: fetchedNodes,
    edges: fetchedEdges,
    isLoading,
    refetch,
  } = useWorkspace(viewState);

  const [nodes, setNodes, onNodesChange] = useNodesState(fetchedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(fetchedEdges);
  const [isLayouting, setIsLayouting] = useState(false);
  const [sidebarTarget, setSidebarTarget] = useState<SidebarTarget | null>(null);
  const [mode, setMode] = useState<GraphMode>("enriched");
  const [activeTerm, setActiveTerm] = useState<LexiconEntry | null>(null);
  const { data: lexicon = [] } = useSWR(
    rawProjectMapId != null ? `/api/graph/${rawProjectMapId}/lexicon/` : null,
    () => fetchLexicon(rawProjectMapId!),
  );
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const flowInstance = useRef<ReactFlowInstance<any, any> | null>(null);
  const clickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fitAll = useCallback(() => {
    setTimeout(() => flowInstance.current?.fitView({ padding: 0.12 }), 0);
  }, []);

  useEffect(() => {
    setSidebarTarget(null);
    setActiveTerm(null);
  }, [level, systemId, containerId]);

  useEffect(() => {
    if (fetchedNodes.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const saved = projectMapId
      ? loadPositions(projectMapId, level, systemId, containerId)
      : null;
    if (saved) {
      const positioned = fetchedNodes.map((n) =>
        saved[n.id] ? { ...n, position: saved[n.id] } : n,
      );
      setNodes(positioned);
      setEdges(fetchedEdges);
      fitAll();
      return;
    }

    setIsLayouting(true);
    applyElkLayout(fetchedNodes, fetchedEdges)
      .then(({ nodes: laidOut, edges: routedEdges }) => {
        setNodes(laidOut);
        setEdges(routedEdges);
        fitAll();
        if (projectMapId) {
          const positions: Record<string, { x: number; y: number }> = {};
          laidOut.forEach((n) => {
            positions[n.id] = n.position;
          });
          savePositions(projectMapId, level, positions, systemId, containerId);
        }
      })
      .finally(() => setIsLayouting(false));
  }, [
    fetchedNodes,
    fetchedEdges,
    setNodes,
    setEdges,
    projectMapId,
    level,
    systemId,
    containerId,
    fitAll,
  ]);

  const onNodeDragStop: OnNodeDrag = useCallback(() => {
    if (!projectMapId) return;
    const positions: Record<string, { x: number; y: number }> = {};
    nodes.forEach((n) => {
      positions[n.id] = n.position;
    });
    savePositions(projectMapId, level, positions, systemId, containerId);
  }, [nodes, projectMapId, level, systemId, containerId]);

  const onNodeDoubleClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      if (clickTimer.current) {
        clearTimeout(clickTimer.current);
        clickTimer.current = null;
      }
      if (level === "C1" && node.type === "system") {
        drillToC2(node.id, (node.data as { label: string }).label);
      } else if (level === "C2" && node.type === "container") {
        drillToC3(node.id, (node.data as { label: string }).label);
      }
    },
    [level, drillToC2, drillToC3],
  );

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    if (clickTimer.current) clearTimeout(clickTimer.current);
    clickTimer.current = setTimeout(() => {
      clickTimer.current = null;
      setSidebarTarget((prev) =>
        prev?.kind === "node" && prev.node.id === node.id
          ? prev
          : { kind: "node", node: node as unknown as RFNode },
      );
    }, 200);
  }, []);

  const onEdgeClick: EdgeMouseHandler = useCallback((_event, edge) => {
    if (clickTimer.current) clearTimeout(clickTimer.current);
    clickTimer.current = setTimeout(() => {
      clickTimer.current = null;
      setSidebarTarget((prev) =>
        prev?.kind === "edge" && prev.edge.id === edge.id
          ? prev
          : { kind: "edge", edge: edge as unknown as RFEdge },
      );
    }, 200);
  }, []);

  const onPaneClick = useCallback(() => {
    if (clickTimer.current) {
      clearTimeout(clickTimer.current);
      clickTimer.current = null;
    }
    setSidebarTarget(null);
  }, []);

  return (
    <LexiconContext.Provider value={{ lexicon, setActiveTerm }}>
    <GraphModeContext.Provider value={mode}>
      <div style={{ width: "100%", height: "100%", position: "relative" }}>
        {/* Shared SVG marker — referenced as url(#c4-arrow) by all FloatingEdge instances */}
        <svg style={{ position: "absolute", width: 0, height: 0, overflow: "hidden" }} aria-hidden="true">
          <defs>
            <marker id="c4-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3.5" orient="auto">
              <polygon points="0 0, 7 3.5, 0 7" className="c4-arrow-fill" />
            </marker>
          </defs>
        </svg>
        <Breadcrumb />

        {/* Mode toggle */}
        <div
          style={{
            position: "absolute",
            top: 40,
            left: 12,
            zIndex: 15,
            display: "flex",
            background: "var(--c4-sidebar-bg)",
            border: "1px solid var(--c4-sidebar-border)",
            borderRadius: 6,
            overflow: "hidden",
          }}
        >
          {(["enriched", "original"] as GraphMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              style={{
                padding: "4px 12px",
                fontSize: 11,
                fontWeight: 600,
                border: "none",
                cursor: "pointer",
                background: mode === m ? "var(--c4-system-border)" : "transparent",
                color: mode === m ? "#fff" : "var(--c4-sidebar-muted)",
                textTransform: "capitalize",
              }}
            >
              {m}
            </button>
          ))}
        </div>

        {(isLoading || isLayouting) && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              zIndex: 10,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "rgba(255,255,255,0.75)",
              pointerEvents: "none",
            }}
          >
            {isLayouting ? "Computing layout…" : "Loading…"}
          </div>
        )}

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodeDoubleClick={onNodeDoubleClick}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onPaneClick={onPaneClick}
          onNodeDragStop={onNodeDragStop}
          onInit={(instance) => {
            flowInstance.current = instance;
          }}
          colorMode="system"
          connectionMode={ConnectionMode.Loose}
          defaultEdgeOptions={{}}
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>

        {rawProjectMapId != null && (
          <OverlaySidebar
            target={sidebarTarget}
            projectMapId={rawProjectMapId}
            onClose={() => setSidebarTarget(null)}
            onSaved={() => refetch?.()}
            onLexiconSaved={() => mutate(`/api/graph/${rawProjectMapId}/lexicon/`)}
          />
        )}
      </div>
    </GraphModeContext.Provider>
    <LexiconBottomPanel entry={activeTerm} onClose={() => setActiveTerm(null)} />
    </LexiconContext.Provider>
  );
}
