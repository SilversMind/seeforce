/*
@c3:component
name: Project Workspace
container: Frontend
technology: React
description: The screen a user lands on for one project — hosts the graph canvas, keeps the current C4 level and drill-down target in the view store, resolves the project's GitHub repo and branch so nodes can link to their source file, and owns the share modal where the owner mints, copies or revokes a share link.
short_desc: Per-project screen — hosts the graph, share modal, and current C4 level
uses:
- Architecture Visualizer: "embeds the graph canvas for the level currently selected in the view store"
- Backend: "reads the project's repo and branch for source links, and creates, reads or revokes its share token"
  technology: REST
*/
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import useSWR from "swr";
import { useViewStore } from "../store/viewStore";
import { C4Graph } from "../components/Graph/C4Graph";
import { getShareToken, createShareToken, revokeShareToken, fetchProjectMap } from "../services/api";

function ShareModal({ projectMapId, onClose }: { projectMapId: number; onClose: () => void }) {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getShareToken(projectMapId).then(setToken).finally(() => setLoading(false));
  }, [projectMapId]);

  async function handleCreate() {
    setLoading(true);
    const t = await createShareToken(projectMapId);
    setToken(t);
    setLoading(false);
  }

  async function handleRevoke() {
    setLoading(true);
    await revokeShareToken(projectMapId);
    setToken(null);
    setLoading(false);
  }

  function copyLink() {
    if (!token) return;
    navigator.clipboard.writeText(`${window.location.origin}/share/${token}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}
      onClick={onClose}>
      <div style={{ background: "var(--c4-sidebar-bg)", border: "1px solid var(--c4-sidebar-border)", borderRadius: 10, padding: 24, width: 400, display: "flex", flexDirection: "column", gap: 16 }}
        onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontWeight: 700, fontSize: 14, color: "var(--c4-sidebar-text)" }}>Share project</span>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--c4-sidebar-muted)", fontSize: 18, cursor: "pointer", lineHeight: 1 }}>×</button>
        </div>

        <p style={{ fontSize: 12, color: "var(--c4-sidebar-muted)", margin: 0 }}>
          Anyone with a SeeForce account can view this project via the share link. Read-only access.
        </p>

        {loading && <div style={{ fontSize: 12, color: "var(--c4-sidebar-muted)" }}>Loading…</div>}

        {!loading && !token && (
          <button onClick={handleCreate}
            style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "8px 0", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
            Generate share link
          </button>
        )}

        {!loading && token && (
          <>
            <div style={{ display: "flex", gap: 8 }}>
              <input readOnly value={`${window.location.origin}/share/${token}`}
                style={{ flex: 1, background: "var(--c4-sidebar-input-bg)", border: "1px solid var(--c4-sidebar-border)", borderRadius: 6, padding: "6px 10px", fontSize: 12, color: "var(--c4-sidebar-text)", outline: "none" }} />
              <button onClick={copyLink}
                style={{ background: copied ? "#22c55e" : "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap" }}>
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <button onClick={handleRevoke}
              style={{ background: "none", color: "#ef4444", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 6, padding: "6px 0", fontSize: 12, cursor: "pointer" }}>
              Revoke link
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export function GraphView() {
  const { id } = useParams<{ id: string }>();
  const projectMapId = parseInt(id!, 10);
  const navigate = useNavigate();
  const setProjectMap = useViewStore((s) => s.setProjectMap);
  const setGithubMeta = useViewStore((s) => s.setGithubMeta);
  const githubRepo = useViewStore((s) => s.githubRepo);
  const githubBranch = useViewStore((s) => s.githubBranch);
  const [shareOpen, setShareOpen] = useState(false);

  const { data: meta } = useSWR(
    !isNaN(projectMapId) ? [projectMapId] : null,
    ([projectMapId]) => fetchProjectMap(projectMapId),
  );

  useEffect(() => {
    if (isNaN(projectMapId)) {
      navigate("/");
      return;
    }
    setProjectMap(projectMapId);
  }, [projectMapId, setProjectMap, navigate]);

  useEffect(() => {
    if (meta) {
      setGithubMeta(meta.github_repo ?? "", meta.github_branch ?? "");
    }
  }, [meta, setGithubMeta]);

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
        {githubRepo && githubBranch && (
          <>
            <span style={{ color: "#475569", fontSize: 12 }}>·</span>
            <span style={{ color: "#64748b", fontSize: 12, fontFamily: "monospace" }}>{githubBranch}</span>
          </>
        )}
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
        <button
          onClick={() => setShareOpen(true)}
          style={{
            background: "#1e293b",
            color: "#94a3b8",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "4px 12px",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          Share
        </button>
      </header>
      <div style={{ flex: 1 }}>
        <C4Graph />
      </div>
      {shareOpen && <ShareModal projectMapId={projectMapId} onClose={() => setShareOpen(false)} />}
    </div>
  );
}
