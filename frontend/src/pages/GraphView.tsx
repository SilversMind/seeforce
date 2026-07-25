import { useViewStore } from "../store/viewStore";
import { C4Graph } from "../components/Graph/C4Graph";
import { UploadPanel } from "../components/UploadPanel";

export function GraphView() {
  const workspaceId = useViewStore((s) => s.workspaceId);

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <header
        style={{
          height: 48,
          background: "#0f172a",
          display: "flex",
          alignItems: "center",
          padding: "0 20px",
          gap: 12,
          flexShrink: 0,
        }}
      >
        <span style={{ color: "white", fontWeight: 700, fontSize: 16 }}>
          C4 Viewer
        </span>
        {workspaceId && (
          <button
            onClick={() => window.location.reload()}
            style={{
              marginLeft: "auto",
              background: "#1e293b",
              color: "#94a3b8",
              border: "1px solid #334155",
              borderRadius: 6,
              padding: "4px 12px",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            ↺ New workspace
          </button>
        )}
      </header>
      <div style={{ flex: 1 }}>
        {workspaceId == null ? <UploadPanel /> : <C4Graph />}
      </div>
    </div>
  );
}
