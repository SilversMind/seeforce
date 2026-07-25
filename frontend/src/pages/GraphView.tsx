import { useEffect } from "react";
import { useViewStore } from "../store/viewStore";
import { fetchLatestProjectMap } from "../services/api";
import { C4Graph } from "../components/Graph/C4Graph";
import { UploadPanel } from "../components/UploadPanel";

export function GraphView() {
  const projectMapId = useViewStore((s) => s.projectMapId);
  const setProjectMap = useViewStore((s) => s.setProjectMap);

  useEffect(() => {
    const es = new EventSource("/api/graph/events/");

    es.onmessage = async (e) => {
      const data = JSON.parse(e.data);
      if (data.type === "scan_complete") {
        setProjectMap(data.id);
      }
    };

    es.onerror = () => {
      es.close();
    };

    // Auto-load latest ProjectMap on first mount
    fetchLatestProjectMap().then((meta) => {
      if (meta && projectMapId == null) {
        setProjectMap(meta.id);
      }
    });

    return () => es.close();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
          SeeForce
        </span>
        {projectMapId && (
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
            ↺ New project
          </button>
        )}
      </header>
      <div style={{ flex: 1 }}>
        {projectMapId == null ? <UploadPanel /> : <C4Graph />}
      </div>
    </div>
  );
}
