import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useViewStore } from "../store/viewStore";
import { C4Graph } from "../components/Graph/C4Graph";

const STORAGE_KEY = "seeforce_preview";

export function PreviewPage() {
  const navigate = useNavigate();
  const setEphemeralWorkspace = useViewStore((s) => s.setEphemeralWorkspace);
  const clearProjectMap = useViewStore((s) => s.clearProjectMap);
  const ephemeralWorkspace = useViewStore((s) => s.ephemeralWorkspace);

  useEffect(() => {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      navigate("/");
      return;
    }
    try {
      setEphemeralWorkspace(JSON.parse(raw));
    } catch {
      navigate("/");
    }
    return () => clearProjectMap();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!ephemeralWorkspace) return null;

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column" }}>
      <div style={{
        background: "#1e3a5f",
        borderBottom: "1px solid #2d5a8e",
        padding: "8px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        fontSize: 13,
        color: "#93c5fd",
        flexShrink: 0,
      }}>
        <span>Preview mode — this visualization is temporary and will be lost on refresh.</span>
        <button
          onClick={() => navigate("/")}
          style={{
            background: "#3b82f6",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            padding: "4px 12px",
            fontSize: 12,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Import from GitHub to save permanently →
        </button>
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <C4Graph />
      </div>
    </div>
  );
}
