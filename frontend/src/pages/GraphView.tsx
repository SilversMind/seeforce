import { useEffect } from "react";
import { mutate } from "swr";
import { useViewStore } from "../store/viewStore";
import { fetchLatestProjectMap } from "../services/api";
import { C4Graph } from "../components/Graph/C4Graph";
import { UploadPanel } from "../components/UploadPanel";

const CLEARED_KEY = "c4:user_cleared";

export function GraphView() {
  const projectMapId = useViewStore((s) => s.projectMapId);
  const setProjectMap = useViewStore((s) => s.setProjectMap);
  const clearProjectMap = useViewStore((s) => s.clearProjectMap);

  useEffect(() => {
    const es = new EventSource("/api/graph/events/");

    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === "scan_complete") {
        sessionStorage.removeItem(CLEARED_KEY);
        setProjectMap(data.id);
        mutate((key) => typeof key === "string" && key.includes("/api/graph/"));
      }
    };

    es.onerror = () => es.close();

    // Auto-load latest ProjectMap unless user explicitly cleared
    if (!sessionStorage.getItem(CLEARED_KEY)) {
      fetchLatestProjectMap().then((meta) => {
        if (meta && projectMapId == null) {
          setProjectMap(meta.id);
        }
      });
    }

    return () => es.close();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleNewProject() {
    sessionStorage.setItem(CLEARED_KEY, "1");
    clearProjectMap();
  }

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
            onClick={handleNewProject}
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
