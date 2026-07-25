/*
@c3:component
name: Edge manager
container: Frontend
description: Handles edge management
*/
import {
  getBezierPath,
  EdgeLabelRenderer,
  BaseEdge,
  type EdgeProps,
} from "@xyflow/react";
import { useGraphMode } from "../../../contexts/GraphModeContext";

export function RelationEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  label,
  data,
  markerEnd,
  markerStart,
}: EdgeProps) {
  const mode = useGraphMode();
  const overlayLabel = (data as { overlay_label?: string } | undefined)?.overlay_label ?? "";
  const displayLabel = mode === "enriched" ? (overlayLabel || (label as string)) : (label as string);

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} markerStart={markerStart} style={{ stroke: "var(--c4-edge-stroke)", strokeWidth: 1.5 }} />
      {displayLabel && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
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
