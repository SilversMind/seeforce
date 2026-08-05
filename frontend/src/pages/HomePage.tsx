import { useState, useEffect } from "react";
import useSWR, { mutate } from "swr";
import { useNavigate } from "react-router-dom";
import { fetchProjectMaps, renameProjectMap, type ProjectMapMeta } from "../services/api";

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

function ProjectCard({
  project,
  onClick,
  onDelete,
  onEdit,
}: {
  project: ProjectMapMeta;
  onClick: () => void;
  onDelete: () => void;
  onEdit: () => void;
}) {
  function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (!window.confirm(`Delete "${project.name}"?`)) return;
    onDelete();
  }

  function handleEdit(e: React.MouseEvent) {
    e.stopPropagation();
    onEdit();
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
      <div style={{ position: "absolute", top: 10, right: 10, display: "flex", gap: 4 }}>
        <button
          onClick={handleEdit}
          title="Rename project"
          style={{ background: "none", border: "none", color: "var(--c4-sidebar-muted)", cursor: "pointer", fontSize: 13, lineHeight: 1, padding: 2 }}
        >
          ✎
        </button>
        <button
          onClick={handleDelete}
          title="Delete project"
          style={{ background: "none", border: "none", color: "var(--c4-sidebar-muted)", cursor: "pointer", fontSize: 16, lineHeight: 1, padding: 2 }}
        >
          ×
        </button>
      </div>
      <div style={{ fontWeight: 700, fontSize: 14, color: "var(--c4-sidebar-text)", paddingRight: 44 }}>
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

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "var(--c4-sidebar-input-bg)",
  border: "1px solid var(--c4-sidebar-border)",
  borderRadius: 6,
  padding: "6px 10px",
  fontSize: 13,
  color: "var(--c4-sidebar-text)",
  outline: "none",
  boxSizing: "border-box",
};

function EditSidebar({
  project,
  onClose,
}: {
  project: ProjectMapMeta | null;
  onClose: () => void;
}) {
  const [name, setName] = useState(project?.name ?? "");
  const [saving, setSaving] = useState(false);

  useEffect(() => { setName(project?.name ?? ""); }, [project]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") handleSave();
    if (e.key === "Escape") onClose();
  }

  async function handleSave() {
    if (!project || !name.trim()) return;
    setSaving(true);
    try {
      await renameProjectMap(project.id, name.trim());
      await mutate("/api/graph/");
      onClose();
    } finally {
      setSaving(false);
    }
  }

  const open = project !== null;

  return (
    <div
      style={{
        position: "fixed",
        top: 48,
        right: 0,
        width: "clamp(280px, 28vw, 420px)",
        height: "calc(100vh - 48px)",
        transform: open ? "translateX(0)" : "translateX(100%)",
        transition: "transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
        background: "var(--c4-sidebar-bg)",
        borderLeft: "1px solid var(--c4-sidebar-border)",
        display: "flex",
        flexDirection: "column",
        zIndex: 20,
        fontSize: 13,
        color: "var(--c4-sidebar-text)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", padding: "12px 16px", borderBottom: "1px solid var(--c4-sidebar-border)", gap: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--c4-sidebar-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Rename project
        </span>
        <button
          onClick={onClose}
          style={{ marginLeft: "auto", background: "none", border: "none", color: "var(--c4-sidebar-muted)", fontSize: 18, cursor: "pointer", lineHeight: 1 }}
        >
          ×
        </button>
      </div>

      <div style={{ flex: 1, padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
        <label style={{ fontSize: 11, color: "var(--c4-sidebar-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Name
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={handleKeyDown}
          style={inputStyle}
          autoFocus={open}
          disabled={!open}
        />
      </div>

      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--c4-sidebar-border)", display: "flex", gap: 8 }}>
        <button
          onClick={handleSave}
          disabled={saving || !name.trim()}
          style={{ flex: 1, background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "8px 0", fontSize: 13, fontWeight: 600, cursor: saving ? "not-allowed" : "pointer", opacity: saving || !name.trim() ? 0.7 : 1 }}
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          onClick={onClose}
          style={{ background: "none", color: "var(--c4-sidebar-muted)", border: "1px solid var(--c4-sidebar-border)", borderRadius: 6, padding: "8px 12px", fontSize: 13, cursor: "pointer" }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export function HomePage() {
  const navigate = useNavigate();
  const [editingProject, setEditingProject] = useState<ProjectMapMeta | null>(null);
  const { data: projects, isLoading, error } = useSWR<ProjectMapMeta[]>(
    "/api/graph/",
    fetchProjectMaps,
  );

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column", background: "var(--c4-page-bg)", position: "relative", overflow: "hidden" }}>
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
              <ProjectCard
                  key={p.id}
                  project={p}
                  onClick={() => navigate(`/project/${p.id}`)}
                  onDelete={() => deleteProject(p.id)}
                  onEdit={() => { setEditingProject(p); }}
                />
            ))}
          </div>
        )}
      </main>

      <EditSidebar project={editingProject} onClose={() => setEditingProject(null)} />
    </div>
  );
}
