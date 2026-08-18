/*
@c3:component
name: Edge manager
container: Frontend
description: Renders directional relationship edges between nodes using floating edge geometry — connects to nearest border point of each node
*/
import { useStore, getBezierPath, Position, EdgeLabelRenderer, BaseEdge, type EdgeProps } from "@xyflow/react";
import type { InternalNode } from "@xyflow/react";
import { useGraphMode } from "../../../contexts/GraphModeContext";

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

export function FloatingEdge({ id, source, target, label, data }: EdgeProps) {
  const sourceNode = useStore((s) => s.nodeLookup.get(source));
  const targetNode = useStore((s) => s.nodeLookup.get(target));
  const mode = useGraphMode();

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
  const displayLabel = mode === "enriched" ? (overlayLabel || (label as string)) : (label as string);

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd="url(#c4-arrow)" style={{ stroke: "var(--c4-edge-stroke)", strokeWidth: 1.5 }} />
      {displayLabel && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              fontSize: 11,
              color: "var(--c4-edge-label-text)",
              padding: "1px 4px",
              pointerEvents: "all",
            }}
          >
            {displayLabel}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
