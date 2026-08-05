import useSWR, { mutate } from "swr";
import { useNavigate } from "react-router-dom";
import { fetchProjectMaps, type ProjectMapMeta } from "../services/api";

function relativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  if (months === 1) return "1 month ago";
  if (months < 12) return `${months} months ago`;
  return `${Math.floor(months / 12)} years ago`;
}

function ProjectCard({ project, onClick, onDelete }: { project: ProjectMapMeta; onClick: () => void; onDelete: () => void }) {
  function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (!window.confirm(`Delete "${project.name}"?`)) return;
    onDelete();
  }

  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--c4-sidebar-bg)",
        border: "1px solid var(--c4-sidebar-border)",
        borderRadius: 8,
        padding: 20,
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        transition: "border-color 0.15s",
        position: "relative",
      }}
      onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "var(--c4-system-border)")}
      onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "var(--c4-sidebar-border)")}
    >
      <button
        onClick={handleDelete}
        title="Delete project"
        style={{
          position: "absolute",
          top: 10,
          right: 10,
          background: "none",
          border: "none",
          color: "var(--c4-sidebar-muted)",
          cursor: "pointer",
          fontSize: 16,
          lineHeight: 1,
          padding: 2,
        }}
      >
        ×
      </button>
      <div style={{ fontWeight: 700, fontSize: 14, color: "var(--c4-sidebar-text)", paddingRight: 20 }}>
        {project.name}
      </div>
      <div style={{ fontSize: 12, color: "var(--c4-sidebar-muted)" }}>
        Updated {relativeDate(project.updated_at)}
      </div>
    </div>
  );
}

async function deleteProject(id: number) {
  await fetch(`/api/graph/${id}/delete/`, { method: "DELETE" });
  await mutate("/api/graph/");
}

export function HomePage() {
  const navigate = useNavigate();
  const { data: projects, isLoading, error } = useSWR<ProjectMapMeta[]>(
    "/api/graph/",
    fetchProjectMaps,
  );

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column", background: "var(--c4-page-bg)" }}>
      <header style={{ height: 48, background: "#0f172a", display: "flex", alignItems: "center", padding: "0 20px", gap: 12, flexShrink: 0 }}>
        <span style={{ color: "white", fontWeight: 700, fontSize: 16 }}>SeeForce</span>
        <button
          onClick={() => navigate("/project/new")}
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
          + New project
        </button>
      </header>

      <main style={{ flex: 1, padding: 32, overflowY: "auto" }}>
        {isLoading && (
          <div style={{ color: "var(--c4-sidebar-muted)", fontSize: 14 }}>Loading…</div>
        )}
        {error && (
          <div style={{ color: "#ef4444", fontSize: 14 }}>Failed to load projects.</div>
        )}
        {projects && projects.length === 0 && (
          <div style={{ textAlign: "center", color: "var(--c4-sidebar-muted)", fontSize: 14, marginTop: 80 }}>
            No projects yet. Scan a codebase to get started.
          </div>
        )}
        {projects && projects.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 16, maxWidth: 1200, margin: "0 auto" }}>
            {projects.map((p) => (
              <ProjectCard key={p.id} project={p} onClick={() => navigate(`/project/${p.id}`)} onDelete={() => deleteProject(p.id)} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
