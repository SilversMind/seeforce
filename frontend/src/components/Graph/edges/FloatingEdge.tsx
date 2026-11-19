/*
@c3:component
name: Edge manager
container: Frontend
description: |
  - Draws directional relationship edges between nodes
  - Attaches each edge to the nearest border point of its nodes
  - Thickens an edge with its number of actions
short_desc: Renders relationship edges between nodes with floating geometry
uses:
- Lexicon: "highlights and links glossary terms found in edge relationship labels"
*/
import { useState } from "react";
import { useStore, getBezierPath, Position, EdgeLabelRenderer, BaseEdge, type EdgeProps } from "@xyflow/react";
import type { InternalNode } from "@xyflow/react";
import { useGraphMode } from "../../../contexts/GraphModeContext";
import { DescriptionWithHighlights } from "../nodes/DescriptionWithHighlights";
import { edgeStrokeWidth } from "../../../lib/nodeSize";

function getCenter(node: InternalNode) {
  const pos = node.internals.positionAbsolute;
  const w = node.measured?.width ?? 180;
  const h = node.measured?.height ?? 64;
  return { x: pos.x + w / 2, y: pos.y + h / 2 };
}

function getBorderIntersection(node: InternalNode, toward: { x: number; y: number }) {
  const center = getCenter(node);
  const hw = (node.measured?.width ?? 180) / 2;
  const hh = (node.measured?.height ?? 64) / 2;
  const dx = toward.x - center.x;
  const dy = toward.y - center.y;
  if (dx === 0 && dy === 0) return { x: center.x, y: center.y, position: Position.Bottom };
  const scaleX = Math.abs(dx) / hw;
  const scaleY = Math.abs(dy) / hh;
  // Which side does the ray exit through?
  let position: Position;
  if (scaleX > scaleY) {
    position = dx > 0 ? Position.Right : Position.Left;
  } else {
    position = dy > 0 ? Position.Bottom : Position.Top;
  }
  const scale = Math.min(hw / Math.abs(dx), hh / Math.abs(dy));
  return { x: center.x + dx * scale, y: center.y + dy * scale, position };
}

export function FloatingEdge({ id, source, target, label, data, selected }: EdgeProps) {
  const sourceNode = useStore((s) => s.nodeLookup.get(source));
  const targetNode = useStore((s) => s.nodeLookup.get(target));
  const mode = useGraphMode();
  const [hovered, setHovered] = useState(false);

  if (!sourceNode || !targetNode) return null;

  const sourceCenter = getCenter(sourceNode);
  const targetCenter = getCenter(targetNode);
  const src = getBorderIntersection(sourceNode, targetCenter);
  const tgt = getBorderIntersection(targetNode, sourceCenter);

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX: src.x, sourceY: src.y, sourcePosition: src.position,
    targetX: tgt.x, targetY: tgt.y, targetPosition: tgt.position,
  });

  const edgeData = data as { overlay_label?: string; short_desc?: string; action_count?: number } | undefined;
  const overlayLabel = edgeData?.overlay_label ?? "";
  const shortLabel = edgeData?.short_desc || (label as string);
  const displayLabel = mode === "enriched" ? (overlayLabel || shortLabel) : shortLabel;
  const actionCount = edgeData?.action_count ?? 0;
  const delta = (data as { delta?: { state: string } } | undefined)?.delta;
  const changed = delta !== undefined && delta.state !== "unchanged";
  const edgeStyle = {
    stroke: changed ? `var(--c4-delta-${delta!.state})` : "var(--c4-edge-stroke)",
    strokeWidth: edgeStrokeWidth(actionCount) + (changed ? 1 : 0),
    ...(delta?.state === "removed" ? { strokeDasharray: "6 4" } : {}),
    // Recessive, not hidden: an unchanged relation stays on the canvas and keeps its label.
    ...(delta?.state === "unchanged" ? { opacity: 0.4 } : {}),
  };

  return (
    <>
      {/* Wider transparent path so hover isn't limited to the thin visible stroke */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={16}
        style={{ pointerEvents: "stroke", cursor: "pointer" }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />
      {/* interactionWidth=0: BaseEdge's own invisible hit-path would otherwise
          paint on top of ours and swallow the hover events before they reach it. */}
      <BaseEdge id={id} path={edgePath} markerEnd="url(#c4-arrow)" interactionWidth={0} style={edgeStyle} />
      {displayLabel && (
        <EdgeLabelRenderer>
          {/* Stays mounted always — toggling mount/unmount on hover makes the
              label (painted above the SVG) cover the hit-path right under the
              cursor, firing mouseleave and flickering the label in and out.
              Toggle visibility/pointerEvents instead so a hidden label never
              intercepts the pointer. */}
          <div
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              opacity: hovered || selected || changed ? 1 : 0,
              pointerEvents: hovered || selected ? "all" : "none",
              maxWidth: 260,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--c4-edge-label-text)", padding: "1px 4px" }}>
              <DescriptionWithHighlights
                text={displayLabel}
                style={hovered || selected ? undefined : { minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
              />
              {actionCount > 1 && (
                <span
                  title={`${actionCount} actions — open the relation to see them all`}
                  style={{ flexShrink: 0, fontSize: 9, fontWeight: 600, padding: "0 4px", borderRadius: 8, border: "1px solid var(--c4-edge-stroke)" }}
                >
                  {actionCount}
                </span>
              )}
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
