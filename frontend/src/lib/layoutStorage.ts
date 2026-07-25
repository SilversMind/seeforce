type PositionMap = Record<string, { x: number; y: number }>;

function key(workspaceId: string, level: string, systemId?: string | null, containerId?: string | null): string {
  return `c4:layout:${workspaceId}:${level}:${systemId ?? ""}:${containerId ?? ""}`;
}

export function loadPositions(
  workspaceId: string,
  level: string,
  systemId?: string | null,
  containerId?: string | null,
): PositionMap | null {
  try {
    const raw = localStorage.getItem(key(workspaceId, level, systemId, containerId));
    return raw ? (JSON.parse(raw) as PositionMap) : null;
  } catch {
    return null;
  }
}

export function savePositions(
  workspaceId: string,
  level: string,
  positions: PositionMap,
  systemId?: string | null,
  containerId?: string | null,
): void {
  try {
    localStorage.setItem(key(workspaceId, level, systemId, containerId), JSON.stringify(positions));
  } catch {
    // storage full or unavailable
  }
}
