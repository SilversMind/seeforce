export interface WorkspaceMeta {
  id: number;
  name: string;
  created_at: string;
}

export interface NodeOverlayKey {
  node_type: string;
  system_name: string;
  container_name: string;
  node_name: string;
}

export interface RFNodeData extends Record<string, unknown> {
  label: string;
  technology: string;
  description: string;
  overlay_label: string;
  overlay_description: string;
  has_overlay: boolean;
  overlay_key: NodeOverlayKey;
}

export interface RFEdgeData extends Record<string, unknown> {
  overlay_label: string;
  has_overlay: boolean;
}

export interface RFNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: RFNodeData;
}

export interface RFEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: string;
  data: RFEdgeData;
}

export interface ReactFlowData {
  nodes: RFNode[];
  edges: RFEdge[];
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

export async function upsertNodeOverlay(
  workspaceId: number,
  key: NodeOverlayKey,
  display_name: string,
  description: string,
): Promise<void> {
  const res = await fetch(`/api/graph/${workspaceId}/overlay/node/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...key, display_name, description }),
  });
  if (!res.ok) throw new Error(`Overlay save failed: ${res.status}`);
}

export async function upsertEdgeOverlay(
  workspaceId: number,
  edge_id: string,
  label: string,
): Promise<void> {
  const res = await fetch(`/api/graph/${workspaceId}/overlay/edge/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edge_id, label }),
  });
  if (!res.ok) throw new Error(`Overlay save failed: ${res.status}`);
}
