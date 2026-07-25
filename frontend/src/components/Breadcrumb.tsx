import { useViewStore } from "../store/viewStore";

export function Breadcrumb() {
  const { level, systemName, containerName, goToC1, goToC2 } = useViewStore();

  if (level === "C1") return null;

  const crumbs: { label: string; onClick: (() => void) | null }[] = [
    { label: "Systems", onClick: goToC1 },
  ];

  if (level === "C2" && systemName) {
    crumbs.push({ label: systemName, onClick: null });
  }

  if (level === "C3") {
    crumbs.push({ label: systemName ?? "System", onClick: goToC2 });
    if (containerName) crumbs.push({ label: containerName, onClick: null });
  }

  return (
    <div
      style={{
        position: "absolute",
        top: 12,
        left: 12,
        zIndex: 10,
        display: "flex",
        alignItems: "center",
        background: "var(--c4-sidebar-bg)",
        border: "1px solid var(--c4-sidebar-border)",
        padding: "5px 12px",
        borderRadius: 6,
        gap: 4,
      }}
    >
      {crumbs.map((crumb, i) => (
        <span key={i} style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {i > 0 && (
            <span style={{ color: "var(--c4-sidebar-muted)", fontSize: 12, margin: "0 2px" }}>›</span>
          )}
          {crumb.onClick ? (
            <button
              onClick={crumb.onClick}
              style={{
                background: "none",
                border: "none",
                color: "var(--c4-system-border)",
                fontSize: 13,
                cursor: "pointer",
                padding: 0,
                fontFamily: "inherit",
                fontWeight: 500,
              }}
            >
              {crumb.label}
            </button>
          ) : (
            <span style={{ fontSize: 13, color: "var(--c4-sidebar-text)", fontWeight: 600 }}>
              {crumb.label}
            </span>
          )}
        </span>
      ))}
    </div>
  );
}
