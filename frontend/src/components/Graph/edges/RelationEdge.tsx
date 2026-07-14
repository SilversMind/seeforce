import { getBezierPath, EdgeLabelRenderer, BaseEdge, type EdgeProps } from "@xyflow/react";

export function RelationEdge({
  id, sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition, label,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });

  return (
    <>
      <BaseEdge id={id} path={edgePath} />
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              fontSize: 11,
              background: "white",
              padding: "1px 4px",
              borderRadius: 3,
              border: "1px solid #e2e8f0",
              pointerEvents: "all",
            }}
          >
            {label as string}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
