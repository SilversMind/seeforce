type PositionMap = Record<string, { x: number; y: number }>;

// Bump this whenever applyElkLayout's algorithm or options change in a way
// that would make previously-saved positions look wrong (e.g. switching
// algorithms). Old cached positions under a stale version are simply never
// looked up again — no manual "clear cache" step needed for the fix to show.
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
