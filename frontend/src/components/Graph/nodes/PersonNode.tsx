import { Handle, Position, type NodeProps } from "@xyflow/react";
import { useGraphMode } from "../../../contexts/GraphModeContext";
import { DescriptionWithHighlights } from "./DescriptionWithHighlights";

export function PersonNode({ data }: NodeProps) {
  const mode = useGraphMode();
  const label = mode === "enriched" ? ((data.overlay_label as string) || (data.label as string)) : (data.label as string);
  const desc = mode === "enriched" ? ((data.overlay_description as string) || (data.description as string)) : (data.description as string);
  const hasOverlay = mode === "enriched" && (data.has_overlay as boolean);

  return (
    <div style={{ padding: 16, background: "var(--c4-person-bg)", border: "2px solid var(--c4-person-border)", borderRadius: 50, minWidth: 120, textAlign: "center", color: "var(--c4-person-text)" }}>
      <Handle id="top-t" type="target" position={Position.Top} />
      <Handle id="top-s" type="source" position={Position.Top} />
      <Handle id="bottom-t" type="target" position={Position.Bottom} />
      <Handle id="bottom-s" type="source" position={Position.Bottom} />
      <Handle id="left-t" type="target" position={Position.Left} />
      <Handle id="left-s" type="source" position={Position.Left} />
      <Handle id="right-t" type="target" position={Position.Right} />
      <Handle id="right-s" type="source" position={Position.Right} />
      <div style={{ fontSize: 24 }}>👤</div>
      <div style={{ fontWeight: 700, fontSize: 13, display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}>
        {label}
        {hasOverlay && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--c4-person-border)", flexShrink: 0 }} />}
      </div>
      {desc && <DescriptionWithHighlights text={desc} style={{ fontSize: 10, color: "var(--c4-person-desc)", marginTop: 4 }} />}
    </div>
  );
}
