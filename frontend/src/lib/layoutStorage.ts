type PositionMap = Record<string, { x: number; y: number }>;

/**
 * Bump whenever applyElkLayout's algorithm/options change in a way that
 * makes previously-saved positions look wrong. Old positions under a stale
 * version are never looked up again — no manual cache-clear needed.
 */
const LAYOUT_VERSION = 2;

function key(workspaceId: string, level: string, systemId?: string | null, containerId?: string | null): string {
  return `c4:layout:v${LAYOUT_VERSION}:${workspaceId}:${level}:${systemId ?? ""}:${containerId ?? ""}`;
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
