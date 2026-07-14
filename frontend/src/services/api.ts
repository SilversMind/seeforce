export interface WorkspaceMeta {
  id: number;
  name: string;
  created_at: string;
}

export interface ReactFlowData {
  nodes: RFNode[];
  edges: RFEdge[];
}

interface RFNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: { label: string; technology: string; description: string };
}

interface RFEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: string;
}

export async function uploadWorkspace(name: string, workspace: unknown): Promise<WorkspaceMeta> {
  const res = await fetch("/api/graph/upload/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, workspace }),
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export function buildViewUrl(
  workspaceId: number,
  level: string,
  systemId: string | null,
  containerId: string | null,
): string {
  const base = `/api/graph/${workspaceId}/view/${level}/`;
  const params = new URLSearchParams();
  if (systemId) params.set("system", systemId);
  if (containerId) params.set("container", containerId);
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}
