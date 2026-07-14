import { Handle, Position, type NodeProps } from "@xyflow/react";

export function ExternalNode({ data }: NodeProps) {
  return (
    <div style={{ padding: 16, background: "#f1f5f9", border: "2px dashed #94a3b8", borderRadius: 8, minWidth: 140 }}>
      <Handle type="target" position={Position.Top} />
      <div style={{ fontWeight: 600, fontSize: 13, color: "#64748b" }}>{data.label as string}</div>
      <div style={{ fontSize: 10, color: "#94a3b8", marginTop: 2 }}>External</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
