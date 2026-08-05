import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { mutate } from "swr";
import { useViewStore } from "../store/viewStore";
import { C4Graph } from "../components/Graph/C4Graph";

export function GraphView() {
  const { id } = useParams<{ id: string }>();
  const projectMapId = parseInt(id!, 10);
  const navigate = useNavigate();
  const setProjectMap = useViewStore((s) => s.setProjectMap);

  useEffect(() => {
    if (isNaN(projectMapId)) {
      navigate("/");
      return;
    }
    setProjectMap(projectMapId);
  }, [projectMapId, setProjectMap, navigate]);

  useEffect(() => {
    const es = new EventSource("/api/graph/events/");

    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === "scan_complete") {
        mutate((key) => typeof key === "string" && key.includes("/api/graph/"));
        navigate(`/project/${data.id}`);
      }
    };

    es.onerror = () => es.close();
    return () => es.close();
  }, [navigate]);

  if (isNaN(projectMapId)) {
    return null;
  }

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column" }}>
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
        <span
          onClick={() => navigate("/")}
          style={{ color: "white", fontWeight: 700, fontSize: 16, cursor: "pointer" }}
        >
          SeeForce
        </span>
        <button
          onClick={() => navigate("/")}
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
          ← Projects
        </button>
      </header>
      <div style={{ flex: 1 }}>
        <C4Graph />
      </div>
    </div>
  );
}
