type PositionMap = Record<string, { x: number; y: number }>;

/**
 * Bump whenever applyElkLayout's algorithm/options change in a way that
 * makes previously-saved positions look wrong. Old positions under a stale
 * version are never looked up again — no manual cache-clear needed.
 */
const LAYOUT_VERSION = 3;

// A comparison gets its own slot so the elements it adds never leak into the ordinary map's layout.
function key(workspaceId: string, level: string, systemId?: string | null, containerId?: string | null, pullRequest?: number | null): string {
  const base = `c4:layout:v${LAYOUT_VERSION}:${workspaceId}:${level}:${systemId ?? ""}:${containerId ?? ""}`;
  return pullRequest != null ? `${base}:pr${pullRequest}` : base;
}

export function loadPositions(
  workspaceId: string,
  level: string,
  systemId?: string | null,
  containerId?: string | null,
  pullRequest?: number | null,
): PositionMap | null {
  try {
    const raw = localStorage.getItem(key(workspaceId, level, systemId, containerId, pullRequest));
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
  pullRequest?: number | null,
): void {
  try {
    localStorage.setItem(key(workspaceId, level, systemId, containerId, pullRequest), JSON.stringify(positions));
  } catch {
    // storage full or unavailable
  }
}
