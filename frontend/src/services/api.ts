export interface AuthUser {
  id: number;
  username: string;
  avatar_url: string;
}

export interface ProjectMapMeta {
  id: number;
  name: string;
  project_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface LexiconEntry {
  term: string;
  definition: string;
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
  code_ref: string;
  overlay_label: string;
  overlay_description: string;
  has_overlay: boolean;
  overlay_key: NodeOverlayKey;
}

export interface RFEdgeEndpoint {
  id: string;
  label: string;
}

export interface RFEdgeData extends Record<string, unknown> {
  overlay_label: string;
  has_overlay: boolean;
  technology: string;
  source_node: RFEdgeEndpoint;
  target_node: RFEdgeEndpoint;
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

export async function uploadProjectMap(name: string, workspace: unknown): Promise<ProjectMapMeta> {
  const res = await fetch("/api/graph/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, workspace }),
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function fetchLatestProjectMap(): Promise<ProjectMapMeta | null> {
  const res = await fetch("/api/graph/latest/");
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
  return res.json();
}

export async function renameProjectMap(id: number, name: string): Promise<ProjectMapMeta> {
  const res = await fetch(`/api/graph/${id}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`Rename failed: ${res.status}`);
  return res.json();
}

export async function fetchProjectMaps(): Promise<ProjectMapMeta[]> {
  const res = await fetch("/api/graph/");
  if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchLexicon(projectMapId: number): Promise<LexiconEntry[]> {
  const res = await fetch(`/api/graph/${projectMapId}/lexicon/`);
  if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
  return res.json();
}

export async function upsertLexiconEntry(projectMapId: number, term: string, definition: string): Promise<void> {
  const res = await fetch(`/api/graph/${projectMapId}/lexicon/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ term, definition }),
  });
  if (!res.ok) throw new Error(`Upsert failed: ${res.status}`);
}

export async function deleteLexiconEntry(projectMapId: number, term: string): Promise<void> {
  const res = await fetch(`/api/graph/${projectMapId}/lexicon/${encodeURIComponent(term)}/`, {
    method: "DELETE",
  });
  if (!res.ok && res.status !== 204) throw new Error(`Delete failed: ${res.status}`);
}

export function buildViewUrl(
  projectMapId: number,
  level: string,
  systemId: string | null,
  containerId: string | null,
): string {
  const base = `/api/graph/${projectMapId}/view/${level}/`;
  const params = new URLSearchParams();
  if (systemId) params.set("system", systemId);
  if (containerId) params.set("container", containerId);
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}

export async function upsertNodeOverlay(
  projectMapId: number,
  key: NodeOverlayKey,
  display_name: string,
  description: string,
): Promise<void> {
  const res = await fetch(`/api/graph/${projectMapId}/overlay/node/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...key, display_name, description }),
  });
  if (!res.ok) throw new Error(`Overlay save failed: ${res.status}`);
}

export async function upsertEdgeOverlay(
  projectMapId: number,
  edge_id: string,
  label: string,
): Promise<void> {
  const res = await fetch(`/api/graph/${projectMapId}/overlay/edge/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edge_id, label }),
  });
  if (!res.ok) throw new Error(`Overlay save failed: ${res.status}`);
}

export async function importFromGitHub(repo: string, branch: string, name?: string): Promise<ProjectMapMeta> {
  const res = await fetch("/api/graph/import/github/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo, branch, name }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error ?? `Import failed: ${res.status}`);
  return body;
}

export async function syncFromGitHub(projectMapId: number): Promise<void> {
  const res = await fetch(`/api/graph/${projectMapId}/sync-github/`, { method: "POST" });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error ?? `Sync failed: ${res.status}`);
}

export async function fetchMe(): Promise<AuthUser | null> {
  const res = await fetch("/api/auth/me/");
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(`fetchMe failed: ${res.status}`);
  return res.json();
}

export async function logout(): Promise<void> {
  const res = await fetch("/api/auth/logout/", { method: "POST" });
  if (!res.ok) throw new Error(`logout failed: ${res.status}`);
}
