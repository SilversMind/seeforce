/*
@c3:component
name: Node manager
container: Frontend
description: Handles node management
*/
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { useGraphMode } from "../../../contexts/GraphModeContext";

export function ComponentNode({ data }: NodeProps) {
  const mode = useGraphMode();
  const label = mode === "enriched" ? ((data.overlay_label as string) || (data.label as string)) : (data.label as string);
  const desc = mode === "enriched" ? ((data.overlay_description as string) || (data.description as string)) : (data.description as string);
  const hasOverlay = mode === "enriched" && (data.has_overlay as boolean);

  return (
    <div
      style={{
        padding: 12,
        background: "var(--c4-component-bg)",
        border: "1px solid var(--c4-component-border)",
        borderRadius: 6,
        minWidth: 140,
        color: "var(--c4-component-text)",
      }}
    >
      <Handle id="top-t" type="target" position={Position.Top} />
      <Handle id="top-s" type="source" position={Position.Top} />
      <Handle id="bottom-t" type="target" position={Position.Bottom} />
      <Handle id="bottom-s" type="source" position={Position.Bottom} />
      <Handle id="left-t" type="target" position={Position.Left} />
      <Handle id="left-s" type="source" position={Position.Left} />
      <Handle id="right-t" type="target" position={Position.Right} />
      <Handle id="right-s" type="source" position={Position.Right} />
      <div style={{ fontWeight: 600, fontSize: 13, display: "flex", alignItems: "center", gap: 4 }}>
        {label}
        {hasOverlay && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--c4-component-border)", flexShrink: 0 }} />}
      </div>
      {(data.technology as string) && (
        <div style={{ fontSize: 10, color: "var(--c4-component-desc)", marginTop: 2 }}>
          {data.technology as string}
        </div>
      )}
      {desc && (
        <div style={{ fontSize: 10, color: "var(--c4-component-desc)", marginTop: 4 }}>{desc}</div>
      )}
    </div>
  );
}
