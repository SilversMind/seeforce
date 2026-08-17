import { Handle, Position, type NodeProps } from "@xyflow/react";
import { useGraphMode } from "../../../contexts/GraphModeContext";
import { DescriptionWithHighlights } from "./DescriptionWithHighlights";

export function SystemNode({ data }: NodeProps) {
  const mode = useGraphMode();
  const label = mode === "enriched" ? ((data.overlay_label as string) || (data.label as string)) : (data.label as string);
  const desc = mode === "enriched" ? ((data.overlay_description as string) || (data.description as string)) : (data.description as string);
  const hasOverlay = mode === "enriched" && (data.has_overlay as boolean);

  return (
    <div style={{ padding: 16, background: "var(--c4-system-bg)", border: "2px solid var(--c4-system-border)", borderRadius: 8, minWidth: 160, color: "var(--c4-system-text)" }}>
      <Handle id="top-t" type="target" position={Position.Top} />
      <Handle id="top-s" type="source" position={Position.Top} />
      <Handle id="bottom-t" type="target" position={Position.Bottom} />
      <Handle id="bottom-s" type="source" position={Position.Bottom} />
      <Handle id="left-t" type="target" position={Position.Left} />
      <Handle id="left-s" type="source" position={Position.Left} />
      <Handle id="right-t" type="target" position={Position.Right} />
      <Handle id="right-s" type="source" position={Position.Right} />
      <div style={{ fontWeight: 700, fontSize: 14, display: "flex", alignItems: "center", gap: 4 }}>
        {label}
        {hasOverlay && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--c4-system-border)", flexShrink: 0 }} />}
      </div>
      {desc && <DescriptionWithHighlights text={desc} style={{ fontSize: 11, color: "var(--c4-system-desc)", marginTop: 4 }} />}
    </div>
  );
}
