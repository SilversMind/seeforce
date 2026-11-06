/*
@c3:component
name: Edge manager
container: Frontend
description: Renders directional relationship edges between nodes using floating edge geometry — connects to nearest border point of each node.
short_desc: Renders relationship edges between nodes with floating geometry
uses:
- Lexicon: "highlights and links glossary terms found in edge relationship labels"
*/
import { useState } from "react";
import { useStore, getBezierPath, Position, EdgeLabelRenderer, BaseEdge, type EdgeProps } from "@xyflow/react";
import type { InternalNode } from "@xyflow/react";
import { useGraphMode } from "../../../contexts/GraphModeContext";
import { DescriptionWithHighlights } from "../nodes/DescriptionWithHighlights";

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

  const overlayLabel = (data as { overlay_label?: string } | undefined)?.overlay_label ?? "";
  const baseLabel = mode === "enriched" ? (overlayLabel || (label as string)) : (label as string);
  const delta = (data as { delta?: { state: string } } | undefined)?.delta;
  const changed = delta !== undefined && delta.state !== "unchanged";
  // The mark carries the state without colour, the way a node's badge does.
  const mark = { added: "+", modified: "~", removed: "−" }[delta?.state ?? ""] ?? "";
  const displayLabel = changed ? `${mark} ${baseLabel}`.trim() : baseLabel;
  const edgeStyle = {
    stroke: changed ? `var(--c4-delta-${delta!.state})` : "var(--c4-edge-stroke)",
    strokeWidth: changed ? 2.5 : 1.5,
    ...(delta?.state === "removed" ? { strokeDasharray: "6 4" } : {}),
    // Recessive, not hidden: an unchanged relation stays on the canvas and keeps its label.
    ...(delta?.state === "unchanged" ? { opacity: 0.4 } : {}),
  };

  return (
    <>
      {/* Wider transparent path so hover isn't limited to the 1.5px visible stroke */}
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
              /* Parallel relations merge into one label, so a changed edge's always-on
                 label is capped to two lines until it is hovered or selected. */
              maxWidth: hovered || selected ? undefined : 260,
              overflow: hovered || selected ? undefined : "hidden",
              display: hovered || selected ? undefined : "-webkit-box",
              WebkitBoxOrient: "vertical",
              WebkitLineClamp: hovered || selected ? undefined : 2,
            }}
          >
            <DescriptionWithHighlights
              text={displayLabel}
              style={{
                fontSize: 11,
                color: "var(--c4-edge-label-text)",
                padding: "1px 4px",
              }}
            />
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
