import { useViewStore } from "../store/viewStore";

export function Breadcrumb() {
  const { level, systemId, containerId, back } = useViewStore();

  const crumbs: string[] = ["C1"];
  if (level === "C2" && systemId) crumbs.push(`C2: ${systemId}`);
  if (level === "C3" && containerId) crumbs.push(`C2`, `C3: ${containerId}`);

  if (level === "C1") return null;

  return (
    <div style={{ position: "absolute", top: 12, left: 12, zIndex: 10, display: "flex", gap: 8, alignItems: "center", background: "white", padding: "6px 12px", borderRadius: 6, boxShadow: "0 1px 4px rgba(0,0,0,0.15)" }}>
      {crumbs.map((c, i) => (
        <span key={i} style={{ color: i < crumbs.length - 1 ? "#94a3b8" : "#0f172a", fontSize: 13 }}>
          {i > 0 && <span style={{ margin: "0 4px", color: "#cbd5e1" }}>›</span>}
          {c}
        </span>
      ))}
      <button onClick={back} style={{ marginLeft: 8, fontSize: 12, cursor: "pointer", background: "#f1f5f9", border: "1px solid #e2e8f0", borderRadius: 4, padding: "2px 8px" }}>
        ← Back
      </button>
    </div>
  );
}
