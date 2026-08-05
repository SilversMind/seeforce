import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadProjectMap } from "../services/api";

export function UploadPanel() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const text = await file.text();
      const workspace = JSON.parse(text);
      const name = workspace.name || file.name.replace(".json", "");
      const meta = await uploadProjectMap(name, workspace);
      navigate(`/project/${meta.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16 }}>
      <h2 style={{ fontSize: 24, fontWeight: 700, color: "#0f172a" }}>SeeForce</h2>
      <p style={{ color: "#64748b", fontSize: 14, textAlign: "center", maxWidth: 360 }}>
        Run <code style={{ background: "#f1f5f9", padding: "1px 6px", borderRadius: 4, fontSize: 13 }}>python manage.py scan --path /your/project</code> to auto-load, or upload a workspace.json manually.
      </p>
      <label style={{ cursor: "pointer", background: "#3b82f6", color: "white", padding: "10px 24px", borderRadius: 8, fontSize: 14, fontWeight: 600 }}>
        {loading ? "Uploading..." : "Choose workspace.json"}
        <input type="file" accept=".json" onChange={handleFile} style={{ display: "none" }} disabled={loading} />
      </label>
      {error && <p style={{ color: "#ef4444", fontSize: 13 }}>{error}</p>}
    </div>
  );
}
