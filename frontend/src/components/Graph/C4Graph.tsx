/*
@c3:component
name: Architecture Visualizer
container: Frontend
technology: ReactFlow
description: Display architecture and manage user interaction such as drilling down on specific component
short_desc: Renders the graph and handles drill-down between C1/C2/C3 views
uses:
- Node manager: "Renders C4 element nodes in the ReactFlow canvas"
- Edge manager: "Renders directional relationship edges between nodes"
- Overlay Editor: "opens the detail/edit panel for the clicked node or edge"
*/
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import useSWR, { mutate } from "swr";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  ConnectionMode,
  useNodesState,
  useEdgesState,
  useNodesInitialized,
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
import { type RFNode, type RFEdge, fetchLexicon, fetchProjectTags } from "../../services/api";
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
  return (
    <ReactFlowProvider>
      <C4GraphInner />
    </ReactFlowProvider>
  );
}

/**
 * Split from the outer component because useNodesInitialized needs a
 * ReactFlowProvider ancestor — the <ReactFlow> element's own provider
 * doesn't exist yet when a sibling's hooks run.
 */
function C4GraphInner() {
  const viewState = useViewStore();
  const {
    drillToC2,
    drillToC3,
    jumpTo,
    level,
    projectMapId: rawProjectMapId,
    shareToken,
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
  /**
   * True while nodes are mounted unpositioned so React Flow can measure
   * their real content-driven size before ELK lays them out with it.
   */
  const [awaitingMeasurement, setAwaitingMeasurement] = useState(false);
  const nodesInitialized = useNodesInitialized();
  const [sidebarTarget, setSidebarTarget] = useState<SidebarTarget | null>(null);
  const [mode, setMode] = useState<GraphMode>("enriched");
  const [activeTerm, setActiveTerm] = useState<LexiconEntry | null>(null);
  const [activeTags, setActiveTags] = useState<Set<string>>(new Set());
  // Share visitors have no account, so the owner-only endpoints would 401 and
  // silently strip the glossary and the tag filter from a shared diagram.
  const lexiconKey = rawProjectMapId == null
    ? null
    : shareToken ? `/api/share/${shareToken}/lexicon/` : `/api/graph/${rawProjectMapId}/lexicon/`;
  const tagsKey = rawProjectMapId == null
    ? null
    : shareToken ? `/api/share/${shareToken}/tags/` : `/api/graph/${rawProjectMapId}/tags/`;
  const { data: lexicon = [] } = useSWR(
    lexiconKey,
    () => fetchLexicon(rawProjectMapId!, shareToken),
  );
  const { data: allProjectTags = [] } = useSWR(
    tagsKey,
    () => fetchProjectTags(rawProjectMapId!, shareToken),
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
    if (!sidebarTarget) return;
    if (sidebarTarget.kind === "node") {
      const updated = nodes.find((n) => n.id === sidebarTarget.node.id);
      if (updated) setSidebarTarget({ kind: "node", node: updated as RFNode });
    } else {
      const updated = edges.find((e) => e.id === sidebarTarget.edge.id);
      if (updated) setSidebarTarget({ kind: "edge", edge: updated as RFEdge });
    }
  }, [nodes, edges]);

  useEffect(() => {
    if (fetchedNodes.length === 0) {
      setNodes([]);
      setEdges([]);
      setAwaitingMeasurement(false);
      return;
    }

    const saved = projectMapId
      ? loadPositions(projectMapId, level, systemId, containerId)
      : null;
    /**
     * A cache is only trustworthy if it covers exactly the current node
     * set — an annotation edit that adds/removes a component means the old
     * positions were computed for a different graph shape and can overlap
     * the new one.
     */
    const savedMatchesCurrentNodes =
      saved !== null &&
      fetchedNodes.length === Object.keys(saved).length &&
      fetchedNodes.every((n) => saved[n.id] !== undefined);
    if (savedMatchesCurrentNodes) {
      const positioned = fetchedNodes.map((n) => ({ ...n, position: saved![n.id] }));
      setNodes(positioned);
      setEdges(fetchedEdges);
      setAwaitingMeasurement(false);
      fitAll();
      return;
    }

    /**
     * Mount at a neutral position first so the measurement pass below can
     * pick up real content-driven box sizes once React Flow has rendered
     * every node — ELK needs those, not an estimate.
     */
    setIsLayouting(true);
    setNodes(fetchedNodes.map((n) => ({ ...n, position: { x: 0, y: 0 } })));
    setEdges(fetchedEdges);
    setAwaitingMeasurement(true);
  }, [fetchedNodes, fetchedEdges, setNodes, setEdges, projectMapId, level, systemId, containerId, fitAll]);

  useEffect(() => {
    if (!awaitingMeasurement || !nodesInitialized) return;

    applyElkLayout(nodes, fetchedEdges)
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
      .finally(() => {
        setIsLayouting(false);
        setAwaitingMeasurement(false);
      });
  }, [awaitingMeasurement, nodesInitialized, nodes, fetchedEdges, setNodes, setEdges, projectMapId, level, systemId, containerId, fitAll]);

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
      const nav = (node.data as { nav?: Parameters<typeof jumpTo>[0] }).nav;
      if (nav) {
        jumpTo(nav);
      } else if (level === "C1" && node.type === "system") {
        drillToC2(node.id, (node.data as { label: string }).label);
      } else if (level === "C2" && node.type === "container") {
        drillToC3(node.id, (node.data as { label: string }).label);
      }
    },
    [level, drillToC2, drillToC3, jumpTo],
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

  const displayNodes = useMemo(() => {
    if (activeTags.size === 0) return nodes;
    return nodes.filter((n) =>
      (n.data.tags as string[] | undefined)?.some((t) => activeTags.has(t)) ?? false
    );
  }, [nodes, activeTags]);

  const displayEdges = useMemo(() => {
    if (activeTags.size === 0) return edges;
    const visibleIds = new Set(displayNodes.map((n) => n.id));
    return edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target));
  }, [edges, displayNodes, activeTags]);

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

        {/* Tag filter panel */}
        {allProjectTags.length > 0 && (
          <div
            style={{
              position: "absolute",
              top: 80,
              left: 12,
              zIndex: 15,
              display: "flex",
              flexWrap: "wrap",
              gap: 4,
              maxWidth: 220,
              background: "var(--c4-sidebar-bg)",
              border: "1px solid var(--c4-sidebar-border)",
              borderRadius: 6,
              padding: "6px 8px",
            }}
          >
            <span style={{ fontSize: 10, color: "var(--c4-sidebar-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", width: "100%", marginBottom: 2 }}>
              Filter by tag
            </span>
            {allProjectTags.map((tag) => {
              const active = activeTags.has(tag);
              return (
                <button
                  key={tag}
                  onClick={() =>
                    setActiveTags((prev) => {
                      const next = new Set(prev);
                      active ? next.delete(tag) : next.add(tag);
                      return next;
                    })
                  }
                  style={{
                    fontSize: 11,
                    padding: "2px 8px",
                    borderRadius: 12,
                    border: `1px solid ${active ? "var(--c4-system-border)" : "var(--c4-sidebar-border)"}`,
                    background: active ? "var(--c4-system-border)" : "transparent",
                    color: active ? "#fff" : "var(--c4-sidebar-muted)",
                    cursor: "pointer",
                  }}
                >
                  {tag}
                </button>
              );
            })}
            {activeTags.size > 0 && (
              <button
                onClick={() => setActiveTags(new Set())}
                style={{ fontSize: 10, padding: "2px 6px", border: "none", background: "none", color: "var(--c4-sidebar-muted)", cursor: "pointer", textDecoration: "underline" }}
              >
                Clear all
              </button>
            )}
          </div>
        )}

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
          nodes={displayNodes}
          edges={displayEdges}
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
            onSaved={() => { refetch?.(); mutate(`/api/graph/${rawProjectMapId}/tags/`); }}
            onLexiconSaved={() => mutate(`/api/graph/${rawProjectMapId}/lexicon/`)}
          />
        )}
      </div>
    </GraphModeContext.Provider>
    <LexiconBottomPanel entry={activeTerm} onClose={() => setActiveTerm(null)} />
    </LexiconContext.Provider>
  );
}
