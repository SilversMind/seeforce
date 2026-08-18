import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useShareToken } from "../services/api";

export function SharePage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    useShareToken(token)
      .then((info) => navigate(`/project/${info.id}`, { replace: true }))
      .catch((e) => setError(e instanceof Error ? e.message : "Invalid share link"));
  }, [token]);

  if (error) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", flexDirection: "column", gap: 12 }}>
        <div style={{ color: "#ef4444", fontSize: 14 }}>{error}</div>
        <button onClick={() => navigate("/")} style={{ background: "none", border: "1px solid #334155", borderRadius: 6, padding: "6px 16px", cursor: "pointer", fontSize: 13, color: "#94a3b8" }}>
          Back to home
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", color: "#94a3b8", fontSize: 14 }}>
      Loading shared project…
    </div>
  );
}
