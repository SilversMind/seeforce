import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useShareToken, type ShareInfo } from "../services/api";
import { useViewStore } from "../store/viewStore";
import { C4Graph } from "../components/Graph/C4Graph";
import { useAuth } from "../contexts/AuthContext";

export function SharePage() {
  const { token } = useParams<{ token: string }>();
  const { user } = useAuth();
  const setShareView = useViewStore((s) => s.setShareView);
  const [info, setInfo] = useState<ShareInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    useShareToken(token)
      .then((data) => {
        setInfo(data);
        setShareView(data.id, token);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Invalid share link"));
  }, [token]);

  if (error) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", flexDirection: "column", gap: 12 }}>
        <div style={{ color: "#ef4444", fontSize: 14 }}>{error}</div>
        <a href="/" style={{ color: "#94a3b8", fontSize: 13 }}>Back to home</a>
      </div>
    );
  }

  if (!info) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", color: "#94a3b8", fontSize: 14 }}>
        Loading…
      </div>
    );
  }

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{ height: 48, background: "#0f172a", display: "flex", alignItems: "center", padding: "0 20px", gap: 12, flexShrink: 0 }}>
        <span style={{ color: "white", fontWeight: 700, fontSize: 16 }}>SeeForce</span>
        <span style={{ color: "#475569", fontSize: 12 }}>·</span>
        <span style={{ color: "#94a3b8", fontSize: 13 }}>{info.name}</span>
        {info.owner_username && (
          <span style={{ color: "#475569", fontSize: 12 }}>by {info.owner_username}</span>
        )}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 11, color: "#475569", background: "#1e293b", border: "1px solid #334155", borderRadius: 4, padding: "2px 8px" }}>
            Read only
          </span>
          {!user && (
            <a
              href="/accounts/github/login/?process=login"
              style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "4px 12px", fontSize: 12, fontWeight: 600, textDecoration: "none" }}
            >
              Sign in with GitHub
            </a>
          )}
          {user && (
            <a href="/" style={{ background: "#1e293b", color: "#94a3b8", border: "1px solid #334155", borderRadius: 6, padding: "4px 12px", fontSize: 12, textDecoration: "none" }}>
              My projects
            </a>
          )}
        </div>
      </header>
      <div style={{ flex: 1 }}>
        <C4Graph />
      </div>
    </div>
  );
}
