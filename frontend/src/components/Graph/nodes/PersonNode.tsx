import { Handle, Position, type NodeProps } from "@xyflow/react";

export function PersonNode({ data }: NodeProps) {
  return (
    <div style={{ padding: 16, background: "#f3e8ff", border: "2px solid #9333ea", borderRadius: 50, minWidth: 120, textAlign: "center" }}>
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: 24 }}>👤</div>
      <div style={{ fontWeight: 700, fontSize: 13 }}>{data.label as string}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
