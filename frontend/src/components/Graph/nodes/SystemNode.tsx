import { Handle, Position, type NodeProps } from "@xyflow/react";

export function SystemNode({ data }: NodeProps) {
  return (
    <div style={{ padding: 16, background: "#dbeafe", border: "2px solid #3b82f6", borderRadius: 8, minWidth: 160 }}>
      <Handle type="target" position={Position.Top} />
      <div style={{ fontWeight: 700, fontSize: 14 }}>{data.label as string}</div>
      {(data.description as string) && <div style={{ fontSize: 11, color: "#555", marginTop: 4 }}>{data.description as string}</div>}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
