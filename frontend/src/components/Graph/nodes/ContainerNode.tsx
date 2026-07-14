import { Handle, Position, type NodeProps } from "@xyflow/react";

export function ContainerNode({ data }: NodeProps) {
  return (
    <div style={{ padding: 16, background: "#dcfce7", border: "2px solid #16a34a", borderRadius: 8, minWidth: 160 }}>
      <Handle type="target" position={Position.Top} />
      <div style={{ fontWeight: 700, fontSize: 14 }}>{data.label as string}</div>
      {(data.technology as string) && (
        <div style={{ fontSize: 10, background: "#16a34a", color: "#fff", borderRadius: 4, padding: "1px 6px", display: "inline-block", marginTop: 4 }}>
          {data.technology as string}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
