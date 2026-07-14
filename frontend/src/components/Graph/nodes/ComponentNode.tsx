import { Handle, Position, type NodeProps } from "@xyflow/react";

export function ComponentNode({ data }: NodeProps) {
  return (
    <div style={{ padding: 12, background: "#fef9c3", border: "1px solid #ca8a04", borderRadius: 6, minWidth: 140 }}>
      <Handle type="target" position={Position.Top} />
      <div style={{ fontWeight: 600, fontSize: 13 }}>{data.label as string}</div>
      {(data.technology as string) && <div style={{ fontSize: 10, color: "#78716c", marginTop: 2 }}>{data.technology as string}</div>}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
