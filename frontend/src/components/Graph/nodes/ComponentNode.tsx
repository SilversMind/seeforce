/*
@c3:component
name: Node manager
container: Frontend
description: Handles node management
*/
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { useGraphMode } from "../../../contexts/GraphModeContext";
import { DescriptionWithHighlights } from "./DescriptionWithHighlights";

export function ComponentNode({ data }: NodeProps) {
  const mode = useGraphMode();
  const label = mode === "enriched" ? ((data.overlay_label as string) || (data.label as string)) : (data.label as string);
  const desc = mode === "enriched" ? ((data.overlay_description as string) || (data.description as string)) : (data.description as string);
  const hasOverlay = mode === "enriched" && (data.has_overlay as boolean);
  const nav = data.nav as { containerName?: string } | undefined;

  return (
    <div
      title={nav ? `Lives in ${nav.containerName} — double-click to view it there` : undefined}
      style={{
        padding: 12,
        background: "var(--c4-component-bg)",
        border: nav ? "1px dashed var(--c4-component-border)" : "1px solid var(--c4-component-border)",
        borderRadius: 6,
        minWidth: 140,
        maxWidth: 440,
        color: "var(--c4-component-text)",
        cursor: nav ? "pointer" : undefined,
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
      {nav?.containerName && (
        <div style={{ fontSize: 10, color: "var(--c4-component-desc)", fontStyle: "italic", marginTop: 2 }}>
          in {nav.containerName}
        </div>
      )}
      {(data.technology as string) && (
        <div style={{ fontSize: 10, color: "var(--c4-component-desc)", marginTop: 2 }}>
          {data.technology as string}
        </div>
      )}
      {desc && <DescriptionWithHighlights text={desc} style={{ fontSize: 10, color: "var(--c4-component-desc)", marginTop: 4 }} />}
    </div>
  );
}
